from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.appointments.models import Slot
from apps.appointments.services import book_appointment
from apps.audit.models import AuditLog
from apps.clinical.models import MedicalRecord
from apps.common.permissions import can
from apps.common.test_data import clinic_data
from apps.patients.models import Patient
from apps.register.models import User
from apps.register.services import create_provider_account, set_account_status
from .models import Provider
from .services import attach_provider_profile, save_provider


class ProviderManagementTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()

    def values(self, **overrides):
        values = dict(actor=self.admin, provider_id=self.provider.pk, provider_type="Physician", license_number=None,
            specialization="Fictional", is_active=True, verification_confirmed=True)
        values.update(overrides)
        return values

    def account_payload(self, **overrides):
        values = dict(school_id="001-Clinic-P", first_name="Fictional", last_name="Practitioner", email="practitioner@example.invalid",
            password1="Private-test-secret-4927!", password2="Private-test-secret-4927!", provider_type="Nurse", license_number="", specialization="")
        values.update(overrides)
        return values

    def test_create_account_is_atomic_inactive_and_cannot_inject_role_or_activation(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("providers:provider_create"), self.account_payload(user_type="Admin", is_active="on", account_status="Suspended"))
        user = User.objects.get(school_id="001-Clinic-P")
        self.assertRedirects(response, reverse("providers:provider_edit", args=[user.pk]))
        self.assertEqual((user.user_type, user.account_status), ("Provider", "Active"))
        self.assertFalse(user.provider_profile.is_active)
        self.assertIsNone(user.provider_profile.license_number)
        self.assertFalse(Patient.objects.filter(pk=user.pk).exists())
        self.assertTrue(user.check_password("Private-test-secret-4927!"))

    def test_duplicate_license_returns_form_error_and_rolls_back_new_user(self):
        Provider.objects.filter(pk=self.provider.pk).update(license_number="SUPPLIED-TEST")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("providers:provider_create"), self.account_payload(license_number="SUPPLIED-TEST"))
        self.assertContains(response, "Please check your details")
        self.assertFalse(User.objects.filter(school_id="001-Clinic-P").exists())

    def test_activation_requires_review_known_designation_and_active_account(self):
        with self.assertRaises(ValidationError):
            save_provider(**self.values(verification_confirmed=False))
        with self.assertRaises(ValidationError):
            save_provider(**self.values(provider_type="Unverified"))
        User.objects.filter(pk=self.provider.pk).update(account_status="Suspended")
        with self.assertRaises(ValidationError):
            save_provider(**self.values())

    def test_post_without_review_shows_checkbox_error_and_does_not_mutate(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("providers:provider_edit", args=[self.provider.pk]), {"provider_type": "Physician", "is_active": "on", "license_number": "NOT-SAVED"})
        self.assertIn("verification_confirmed", response.context["form"].errors)
        self.provider.refresh_from_db()
        self.assertIsNone(self.provider.license_number)

    def test_wrong_role_and_stale_actor_cannot_update_or_attach(self):
        User.objects.filter(pk=self.admin.pk).update(account_status="Suspended")
        for actor in (self.admin, self.patient.patient, self.provider.provider, None):
            with self.assertRaises(PermissionDenied):
                save_provider(**self.values(actor=actor))
            with self.assertRaises(PermissionDenied):
                attach_provider_profile(actor=actor, user_id=self.admin.pk)

    def test_existing_admin_can_receive_provider_profile_without_losing_patient_or_role(self):
        Patient.objects.create(patient=self.admin, affiliation="Staff")
        provider = attach_provider_profile(actor=self.admin, user_id=self.admin.pk)
        self.assertFalse(provider.is_active)
        self.assertEqual(provider.provider_type, "Unverified")
        save_provider(**self.values(provider_id=self.admin.pk, provider_type="Dentist"))
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.user_type, "Admin")
        self.assertEqual(self.admin.patient_profile.affiliation, "Staff")
        self.assertTrue(can(self.admin, "schedule.manage", provider))
        with self.assertRaises(ValidationError):
            attach_provider_profile(actor=self.admin, user_id=self.admin.pk)
        with self.assertRaises(ValidationError):
            attach_provider_profile(actor=self.admin, user_id=self.patient.pk)

    def test_deactivation_preserves_history_disables_future_slots_and_not_reopened(self):
        save_provider(**self.values(is_active=False, license_number=" "))
        self.slot.refresh_from_db()
        self.provider.refresh_from_db()
        self.record.refresh_from_db()
        self.assertFalse(self.slot.is_active)
        self.assertFalse(self.provider.is_active)
        self.assertIsNone(self.provider.license_number)
        self.assertEqual(self.record.provider_id, self.provider.pk)
        self.assertEqual(self.record.status, "Finalized")
        save_provider(**self.values())
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.is_active)

    def test_live_booking_and_draft_encounter_prevent_deactivation(self):
        appointment = book_appointment(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="Fictional", actor=self.admin)
        with self.assertRaises(ValidationError):
            save_provider(**self.values(is_active=False))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "Scheduled")
        MedicalRecord.objects.create(patient=self.patient, provider=self.provider, chief_complaint="Draft")
        with self.assertRaises(ValidationError):
            save_provider(**self.values(is_active=False))

    def test_referenced_known_designation_is_preserved_but_reviewed_legacy_unknown_can_be_reconciled(self):
        with self.assertRaises(ValidationError):
            save_provider(**self.values(provider_type="Dentist"))
        Provider.objects.filter(pk=self.provider.pk).update(provider_type="Unverified", is_active=False)
        Slot.objects.filter(pk=self.slot.pk).update(is_active=False)
        save_provider(**self.values(provider_type="Physician"))
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, "Finalized")
        self.assertEqual(self.record.provider_id, self.provider.pk)

    def test_suspended_provider_cannot_create_availability_or_encounters(self):
        set_account_status(actor=self.admin, user_id=self.provider.pk, status="Suspended")
        with self.assertRaises(ValidationError):
            Slot.objects.create(provider=self.provider, room=self.slot.room, is_active=True,
                start_time=self.slot.start_time + timedelta(days=1), end_time=self.slot.end_time + timedelta(days=1))
        with self.assertRaises(ValidationError):
            MedicalRecord.objects.create(provider=self.provider, patient=self.patient, chief_complaint="Denied")

    def test_nurse_activation_does_not_grant_finalize_or_prescribing_permission(self):
        user = create_provider_account(actor=self.admin, school_id="NURSE", email="nurse@example.invalid", first_name="Test", last_name="Nurse", password="Private-secret-5927!")
        provider = save_provider(**self.values(provider_id=user.pk, provider_type="Nurse"))
        draft = MedicalRecord.objects.create(patient=self.patient, provider=provider, chief_complaint="Triage")
        self.assertTrue(can(user, "vitals.record", draft))
        self.assertFalse(can(user, "record.finalize", draft))
        self.assertFalse(can(user, "prescription.issue", draft))

    def test_ineligible_primary_role_cannot_receive_bookings_despite_a_stale_active_slot(self):
        User.objects.filter(pk=self.provider.pk).update(user_type="Patient")
        with self.assertRaises(ValidationError):
            book_appointment(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="Denied", actor=self.admin)
        self.assertFalse(self.slot.appointments.exists())

    def test_audit_failure_rolls_back_provider_and_slot_state(self):
        with patch("apps.providers.services.AuditLog.objects.create", side_effect=ValidationError("Audit unavailable")):
            with self.assertRaises(ValidationError):
                save_provider(**self.values(is_active=False))
        self.provider.refresh_from_db()
        self.slot.refresh_from_db()
        self.assertTrue(self.provider.is_active)
        self.assertTrue(self.slot.is_active)
        self.assertFalse(AuditLog.objects.exists())
