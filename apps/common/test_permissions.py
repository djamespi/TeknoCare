from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from apps.appointments.services import book_appointment, cancel_appointment
from apps.clinical.models import MedicalRecord
from apps.patients.models import Patient
from apps.providers.models import Provider
from apps.register.models import User
from .permissions import can, require_permission
from .test_data import clinic_data


class AccessPolicyTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.doctor, self.slot, self.finalized = clinic_data()
        self.other = User.objects.create_user("OTHER-PATIENT", "other@example.invalid", "test-password")
        self.other_patient = Patient.objects.create(patient=self.other, affiliation="Staff")
        self.draft = MedicalRecord.objects.create(patient=self.patient, provider=self.doctor, chief_complaint="Fictional draft")

    def practitioner(self, designation="Nurse", active=True):
        user = User.objects.create_user(f"{designation}-{active}", f"{designation}-{active}@example.invalid", "test-password", user_type="Provider")
        return Provider.objects.create(provider=user, provider_type=designation, is_active=active)

    def test_default_deny_and_fresh_account_role_status(self):
        for actor in (None, AnonymousUser(), self.other):
            self.assertFalse(can(actor, "accounts.manage"))
        self.assertTrue(can(self.admin, "accounts.manage"))
        User.objects.filter(pk=self.admin.pk).update(user_type="Patient")
        self.assertFalse(can(self.admin, "accounts.manage"))
        User.objects.filter(pk=self.doctor.pk).update(account_status="Suspended")
        with self.assertRaises(PermissionDenied):
            require_permission(self.doctor.provider, "record.finalize", self.draft)
        self.assertFalse(can(self.other, "unknown.action", self.other_patient))

    def test_ownership_and_admin_operations_do_not_imply_clinical_authority(self):
        self.assertTrue(can(self.patient.patient, "patient.view", self.patient))
        self.assertFalse(can(self.other, "patient.view", self.patient))
        self.assertTrue(can(self.admin, "patient.view", self.patient))
        for action in ("record.view", "vitals.record", "record.finalize", "prescription.issue"):
            self.assertFalse(can(self.admin, action, self.draft))
        self.assertFalse(can(self.doctor.provider, "billing.manage"))
        self.assertFalse(can(self.other, "schedule.manage", self.doctor))
        self.assertTrue(can(self.doctor.provider, "schedule.manage", self.doctor))

    def test_patient_can_only_read_own_finalized_summary(self):
        self.assertTrue(can(self.patient.patient, "record.view", self.finalized))
        self.assertFalse(can(self.patient.patient, "record.view", self.draft))
        self.assertFalse(can(self.other, "record.view", self.finalized))

    def test_only_assigned_active_physician_or_dentist_may_finalize_and_prescribe(self):
        dentist = self.practitioner("Dentist")
        for designation in ("Nurse", "Unverified"):
            provider = self.practitioner(designation)
            for action in ("record.finalize", "prescription.issue"):
                self.assertFalse(can(provider.provider, action, self.draft))
        for action in ("record.finalize", "prescription.issue"):
            self.assertTrue(can(self.doctor.provider, action, self.draft))
            self.assertFalse(can(dentist.provider, action, self.draft))
            self.assertFalse(can(self.doctor.provider, action, self.finalized))
        self.draft.provider = dentist
        self.draft.save()
        self.assertTrue(can(dentist.provider, "record.finalize", self.draft))
        Provider.objects.filter(pk=dentist.pk).update(is_active=False)
        self.assertFalse(can(dentist.provider, "prescription.issue", self.draft))

    def test_nurse_triage_is_current_day_draft_only_not_clinical_notes(self):
        nurse = self.practitioner()
        self.assertTrue(can(nurse.provider, "patient.view", self.patient))
        self.assertTrue(can(nurse.provider, "vitals.record", self.draft))
        self.assertFalse(can(nurse.provider, "record.view", self.draft))
        self.assertFalse(can(nurse.provider, "vitals.record", self.finalized))
        self.draft.visited_at -= timedelta(days=2)
        self.draft.save()
        self.assertFalse(can(nurse.provider, "vitals.record", self.draft))
        self.assertFalse(can(nurse.provider, "patient.view", self.patient))

    def test_unassigned_clinician_needs_current_care_relationship_for_history(self):
        dentist = self.practitioner("Dentist")
        self.assertFalse(can(dentist.provider, "patient.view", self.patient))
        self.assertFalse(can(dentist.provider, "record.view", self.finalized))
        current = MedicalRecord.objects.create(patient=self.patient, provider=dentist, chief_complaint="Follow up")
        self.assertTrue(can(dentist.provider, "record.view", self.finalized))
        self.assertFalse(can(dentist.provider, "record.view", self.draft))
        self.assertTrue(can(dentist.provider, "record.finalize", current))

    def test_admin_with_qualified_provider_profile_may_treat_others_but_not_self(self):
        provider = Provider.objects.create(provider=self.admin, provider_type="Physician", is_active=True)
        self.draft.provider = provider
        self.draft.save()
        self.assertTrue(can(self.admin, "record.finalize", self.draft))
        patient = Patient.objects.create(patient=self.admin, affiliation="Staff")
        own_record = MedicalRecord.objects.create(patient=patient, provider=provider, chief_complaint="Self care denied")
        for action in ("vitals.record", "record.finalize", "prescription.issue"):
            self.assertFalse(can(self.admin, action, own_record))

    def test_booking_cancellation_enforce_actor_ownership_and_state(self):
        values = dict(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="Fictional booking")
        with self.assertRaises(PermissionDenied):
            book_appointment(**values, actor=self.other)
        appointment = book_appointment(**values, actor=self.patient.patient)
        with self.assertRaises(PermissionDenied):
            cancel_appointment(appointment_id=appointment.pk, actor=self.other)
        appointment.status = "Checked-In"
        appointment.save()
        with self.assertRaises(PermissionDenied):
            cancel_appointment(appointment_id=appointment.pk, actor=self.admin)
        self.assertEqual(appointment.status, "Checked-In")

    def test_booking_rechecks_provider_activation_and_future_time(self):
        values = dict(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="Fictional booking", actor=self.admin)
        Provider.objects.filter(pk=self.doctor.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            book_appointment(**values)
        Provider.objects.filter(pk=self.doctor.pk).update(is_active=True)
        with patch("apps.appointments.services.timezone.now", return_value=self.slot.end_time):
            with self.assertRaises(ValidationError):
                book_appointment(**values)

    def test_past_or_encounter_linked_bookings_cannot_be_canceled(self):
        appointment = book_appointment(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="Visit", actor=self.admin)
        with patch("apps.common.permissions.timezone.now", return_value=self.slot.end_time):
            self.assertFalse(can(self.admin, "appointment.cancel", appointment))
        MedicalRecord.objects.create(patient=self.patient, provider=self.doctor, appointment=appointment, chief_complaint="Visit")
        self.assertFalse(can(self.admin, "appointment.cancel", appointment))
        self.assertTrue(self.slot.appointments.exists())
