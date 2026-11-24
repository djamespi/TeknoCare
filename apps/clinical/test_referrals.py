from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.common.test_data import clinic_data
from apps.providers.models import Provider
from apps.register.models import User

from .consultation import consultation_version, finalize_consultation
from .models import MedicalRecord, Referral
from .referrals import create_referral, update_referral_status


class ReferralTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.doctor, _, cls.finalized = clinic_data()
        cls.visit = MedicalRecord.objects.create(patient=cls.patient, provider=cls.doctor,
            chief_complaint="Fictional complaint", symptoms="Fictional symptoms", treatment_plan="Fictional plan")
        nurse = User.objects.create_user("REFERRAL-NURSE", "referral-nurse@example.invalid", user_type="Provider")
        cls.nurse = Provider.objects.create(provider=nurse, is_active=True, provider_type="Nurse")

    def create(self):
        return create_referral(actor=self.doctor.provider, record_id=self.visit.pk,
            destination="Fictional Clinic", reason="Fictional patient-facing instructions.")

    def test_assigned_clinician_creates_pending_with_server_identity(self):
        self.client.force_login(self.doctor.provider)
        create_url = reverse("consultation:referral_create", args=[self.visit.pk])
        list_url = reverse("consultation:referrals", args=[self.visit.pk])
        self.assertContains(self.client.get(create_url), "Patient-facing reason and instructions")
        invalid = self.client.post(create_url, {"destination": "Clinic", "reason": "  "})
        self.assertContains(invalid, "This field is required")
        self.assertFalse(Referral.objects.exists())
        self.assertRedirects(self.client.post(create_url, {
            "destination": "  Fictional Clinic  ", "reason": "  Bring your fictional visit note.  ",
            "status": "Completed", "referred_by_provider": self.nurse.pk,
        }), list_url)
        referral = self.visit.referrals.get()
        self.assertEqual((referral.status, referral.referred_by_provider_id), ("Pending", self.doctor.pk))
        self.assertEqual(referral.destination, "Fictional Clinic")
        self.assertEqual(referral.reason, "Bring your fictional visit note.")
        self.assertTrue(AuditLog.objects.filter(actor_user_id=self.doctor.pk, target_table="referral",
            target_record_id=referral.pk, action_performed="Referral recorded").exists())

    def test_admin_patient_and_nurse_cannot_use_clinician_actions(self):
        referral = self.create()
        for account, status in ((self.admin, 403), (self.patient.patient, 403), (self.nurse.provider, 404)):
            self.client.force_login(account)
            self.assertEqual(self.client.post(reverse("consultation:referral_create", args=[self.visit.pk])).status_code, status)
            self.assertEqual(self.client.post(reverse("consultation:referral_follow_up", args=[self.visit.pk, referral.pk]),
                {"status": "Canceled", "confirm": "on"}).status_code, status)
        secured = Client(enforce_csrf_checks=True)
        secured.force_login(self.doctor.provider)
        self.assertEqual(secured.post(reverse("consultation:referral_create", args=[self.visit.pk])).status_code, 403)
        referral.refresh_from_db()
        self.assertEqual(referral.status, "Pending")

    def test_follow_up_after_finalization_preserves_content_and_refuses_replay(self):
        referral = self.create()
        finalize_consultation(actor=self.doctor.provider, record_id=self.visit.pk,
            expected_version=consultation_version(self.visit, (), None))
        self.client.force_login(self.doctor.provider)
        create_url = reverse("consultation:referral_create", args=[self.visit.pk])
        self.assertEqual(self.client.get(create_url).status_code, 403)
        follow_up = reverse("consultation:referral_follow_up", args=[self.visit.pk, referral.pk])
        wrong_visit = reverse("consultation:referral_follow_up", args=[self.finalized.pk, referral.pk])
        self.assertEqual(self.client.get(wrong_visit).status_code, 404)
        values = {"status": "Completed", "confirm": "on", "destination": "Rewritten destination", "reason": "Rewritten reason"}
        self.assertRedirects(self.client.post(follow_up, values), reverse("consultation:referrals", args=[self.visit.pk]))
        referral.refresh_from_db()
        self.assertEqual((referral.status, referral.destination, referral.reason, referral.referred_by_provider_id),
            ("Completed", "Fictional Clinic", "Fictional patient-facing instructions.", self.doctor.pk))
        self.assertContains(self.client.post(follow_up, {"status": "Canceled", "confirm": "on"}), "already has a final")
        self.assertNotContains(self.client.get(follow_up), "Save follow-up")
        self.assertEqual(AuditLog.objects.filter(target_table="referral", target_record_id=referral.pk,
            action_performed="Referral marked completed").count(), 1)

    def test_services_and_database_reject_invalid_lifecycle_writes(self):
        referral = self.create()
        for action in (
            lambda: Referral.objects.filter(pk=referral.pk).update(reason="Rewrite during Draft"),
            lambda: Referral.objects.filter(pk=referral.pk).delete(),
            lambda: Referral.objects.bulk_create([Referral(record=self.finalized, referred_by_provider=self.doctor,
                destination="Fictional", reason="Late creation")]),
            lambda: Referral.objects.bulk_create([Referral(record=self.visit, referred_by_provider=self.nurse,
                destination="Fictional", reason="Invalid author")]),
        ):
            with self.assertRaises(IntegrityError), transaction.atomic():
                action()
        with self.assertRaises(PermissionDenied):
            create_referral(actor=self.doctor.provider, record_id=self.finalized.pk, destination="Fictional", reason="Late")
        arguments = {"actor": self.doctor.provider, "record_id": self.visit.pk, "referral_id": referral.pk}
        with self.assertRaisesMessage(ValidationError, "Choose Completed or Canceled"):
            update_referral_status(**arguments, status="Pending")
        update_referral_status(**arguments, status="Canceled")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Referral.objects.filter(pk=referral.pk).update(status="Pending")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Referral.objects.filter(pk=referral.pk).update(status="Completed")
