from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment, Slot
from apps.audit.models import AuditLog
from apps.common.test_data import clinic_data
from apps.patients.models import Affiliation, Patient
from apps.providers.models import Provider
from apps.register.models import User

from .models import MedicalRecord
from .reception import assign_encounter, change_appointment_status, open_scheduled_encounter, open_walkin_encounter


def attending(designation):
    account = User.objects.create_user(f"RECEPTION-{designation}", f"reception-{designation}@example.invalid",
        user_type=User.UserType.PROVIDER, fname="Fictional", lname=designation)
    return Provider.objects.create(provider=account, provider_type=designation, is_active=True)


def appointment_at(patient, provider, room, start, end):
    slot = Slot.objects.create(provider=provider, room=room, start_time=start, end_time=end, is_active=True)
    return Appointment.objects.create(patient=patient, slot=slot, reason_for_visit="Fictional private reason")


class ReceptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.provider, cls.future_slot, cls.finalized = clinic_data()
        cls.nurse = attending(Provider.Type.NURSE)
        cls.dentist = attending(Provider.Type.DENTIST)
        now = timezone.now()
        cls.current = appointment_at(cls.patient, cls.provider, cls.future_slot.room,
            now - timedelta(minutes=2), now + timedelta(minutes=15))
        cls.future = Appointment.objects.create(patient=cls.patient, slot=cls.future_slot, reason_for_visit="Fictional future")
        cls.past = appointment_at(cls.patient, cls.provider, cls.future_slot.room,
            now - timedelta(days=1, minutes=30), now - timedelta(days=1))

    def transition(self, action, appointment=None, actor=None):
        return change_appointment_status(actor=actor or self.admin, appointment_id=(appointment or self.current).pk, action=action)

    def open_scheduled(self, provider=None, actor=None):
        return open_scheduled_encounter(actor=actor or self.admin, appointment_id=self.current.pk,
            provider_id=(provider or self.provider).pk)

    def test_queue_is_scoped_and_reception_does_not_display_clinical_notes(self):
        url = reverse("reception:queue")
        detail = reverse("reception:appointment", args=[self.current.pk])
        self.client.force_login(self.patient.patient)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.dentist.provider)
        self.assertNotContains(self.client.get(url), detail)
        self.assertEqual(self.client.get(detail).status_code, 404)
        for actor in (self.admin, self.provider.provider, self.nurse.provider):
            self.client.force_login(actor)
            result = self.client.get(url)
            self.assertContains(result, detail)
            self.assertNotContains(result, reverse("reception:appointment", args=[self.future.pk]))
            self.assertNotContains(self.client.get(detail), self.current.reason_for_visit)
        detail = reverse("reception:encounter", args=[self.finalized.pk])
        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get(detail), self.finalized.chief_complaint)

    def test_check_in_and_open_draft_through_the_normal_pages(self):
        self.client.force_login(self.admin)
        url = reverse("reception:appointment", args=[self.current.pk])
        self.assertContains(self.client.get(url), "Check in patient")
        self.current.refresh_from_db()
        self.assertEqual(self.current.status, Appointment.Status.SCHEDULED)
        self.assertRedirects(self.client.post(url, {"action": "check_in"}), url)
        response = self.client.post(url, {"action": "open", "provider": self.dentist.pk}, follow=True)
        self.assertContains(response, "Draft encounter opened.")
        self.assertContains(response, "Scheduled provider")
        self.assertContains(response, "Attending provider")
        visit = MedicalRecord.objects.get(appointment=self.current)
        self.assertEqual((visit.status, visit.provider_id, visit.affiliation_at_visit, visit.chief_complaint),
            (MedicalRecord.Status.DRAFT, self.dentist.pk, Affiliation.STUDENT, ""))
        with self.assertRaisesMessage(ValidationError, "already linked"):
            self.open_scheduled(self.dentist)

    def test_transitions_are_limited_by_timing_status_and_finalized_care(self):
        with self.assertRaisesMessage(ValidationError, "before opening"):
            self.open_scheduled()
        with self.assertRaisesMessage(ValidationError, "clinic day"):
            self.transition("check_in", self.future)
        with self.assertRaisesMessage(ValidationError, "only after"):
            self.transition("no_show")
        self.assertEqual(self.transition("no_show", self.past).status, Appointment.Status.NO_SHOW)
        with self.assertRaises(ValidationError):
            self.transition("check_in", self.past)
        self.transition("check_in")
        visit = self.open_scheduled()
        with self.assertRaisesMessage(ValidationError, "finalized encounter"):
            self.transition("complete")
        visit.status, visit.finalized_at = MedicalRecord.Status.FINALIZED, timezone.now()
        with self.assertRaisesMessage(ValidationError, "chief complaint"):
            visit.save()
        visit.chief_complaint = "Fictional completed encounter"
        visit.save()
        self.assertEqual(self.transition("complete").status, Appointment.Status.COMPLETED)
        with self.assertRaises(ValidationError):
            self.transition("complete")

    def test_forged_provider_and_cross_scope_mutations_are_denied(self):
        with self.assertRaises(PermissionDenied):
            self.transition("check_in", actor=self.dentist.provider)
        self.transition("check_in", actor=self.nurse.provider)
        with self.assertRaises(PermissionDenied):
            self.open_scheduled(self.dentist, actor=self.provider.provider)
        visit = self.open_scheduled(actor=self.provider.provider)
        with self.assertRaises(PermissionDenied):
            assign_encounter(actor=self.provider.provider, record_id=visit.pk,
                provider_id=self.dentist.pk, expected_provider_id=self.provider.pk)
        result = assign_encounter(actor=self.nurse.provider, record_id=visit.pk,
            provider_id=self.dentist.pk, expected_provider_id=self.provider.pk)
        self.assertEqual(result.provider_id, self.dentist.pk)
        self.assertEqual(result.appointment.slot.provider_id, self.provider.pk)
        with self.assertRaisesMessage(ValidationError, "changed"):
            assign_encounter(actor=self.admin, record_id=visit.pk,
                provider_id=self.provider.pk, expected_provider_id=self.provider.pk)

    def test_walkin_exact_lookup_uses_affiliation_and_prevents_duplicate_draft(self):
        url = reverse("reception:walkin_lookup")
        self.client.force_login(self.nurse.provider)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        detail_url = reverse("reception:walkin_create", args=[self.patient.pk])
        lookup = self.client.get(url, {"school_id": self.patient.patient.school_id})
        self.assertContains(lookup, detail_url)
        response = self.client.post(detail_url, {"provider": self.provider.pk, "affiliation": "Faculty"}, follow=True)
        self.assertContains(response, "Walk-in encounter opened.")
        visit = MedicalRecord.objects.get(status=MedicalRecord.Status.DRAFT)
        self.assertIsNone(visit.appointment_id)
        self.assertEqual(visit.affiliation_at_visit, Affiliation.STUDENT)
        self.assertContains(self.client.post(detail_url, {"provider": self.provider.pk}), "already has an open walk-in")
        self.assertEqual(MedicalRecord.objects.filter(status=MedicalRecord.Status.DRAFT).count(), 1)

    def test_opening_requires_reviewed_affiliation_and_current_provider(self):
        Patient.objects.filter(pk=self.patient.pk).update(affiliation=None)
        with self.assertRaisesMessage(ValidationError, "Verify patient affiliation"):
            open_walkin_encounter(actor=self.admin, patient_id=self.patient.pk, provider_id=self.provider.pk)
        Provider.objects.filter(pk=self.provider.pk).update(is_active=False)
        with self.assertRaisesMessage(ValidationError, "Choose an active provider"):
            open_walkin_encounter(actor=self.admin, patient_id=self.patient.pk, provider_id=self.provider.pk)
        self.assertFalse(AuditLog.objects.exists())

    def test_admin_cancellation_and_csrf(self):
        url = reverse("reception:appointment", args=[self.future.pk])
        protected_client = Client(enforce_csrf_checks=True)
        protected_client.force_login(self.admin)
        self.assertEqual(protected_client.post(url, {"action": "cancel"}).status_code, 403)
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(url, {"action": "cancel"}), url)
        self.future.refresh_from_db()
        self.assertEqual(self.future.status, Appointment.Status.CANCELED)
        self.assertTrue(AuditLog.objects.filter(action_performed="Appointment canceled by Admin").exists())


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class ConcurrentIntakeTests(TransactionTestCase):
    available_apps = settings.INSTALLED_APPS

    def test_duplicate_requests_open_one_scheduled_encounter(self):
        admin, patient, provider, slot, _ = clinic_data()
        now = timezone.now()
        item = appointment_at(patient, provider, slot.room, now - timedelta(minutes=2), now + timedelta(minutes=10))
        change_appointment_status(actor=admin, appointment_id=item.pk, action="check_in")
        gate = Barrier(2, timeout=10)

        def attempt(_):
            close_old_connections()
            try:
                gate.wait()
                open_scheduled_encounter(actor=admin, appointment_id=item.pk, provider_id=provider.pk)
                return "opened"
            except ValidationError as error:
                self.assertIn("already linked", str(error))
                return "duplicate"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(list(executor.map(attempt, range(2), timeout=20)), ["opened", "duplicate"])
        self.assertEqual(MedicalRecord.objects.filter(appointment=item).count(), 1)
