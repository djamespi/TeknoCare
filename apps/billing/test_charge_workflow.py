import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clinical.models import MedicalRecord
from apps.common.test_data import clinic_data
from apps.patients.models import Affiliation, Patient
from apps.register.models import User

from .models import AcademicTerm, StudentCharge
from .services import create_charge


class TuitionWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.provider, _, cls.visit = clinic_data()
        cls.term = AcademicTerm.objects.create(
            academic_year="2026-2027", semester="First", start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 31), is_open_for_charges=True,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def create_url(self, visit):
        return reverse("billing:charge_create", args=[visit.pk])

    def detail_url(self, charge):
        return reverse("billing:charge_detail", args=[charge.pk])

    def payload(self, **overrides):
        return {
            "term": self.term.pk, "request_code": uuid4(), "description": "Clinic service (prototype)",
            "amount": "125.50", **overrides,
        }

    def service_charge(self, visit=None, term=None, description="Clinic service (prototype)"):
        return create_charge(
            actor=self.admin, record_id=(visit or self.visit).pk, term_id=(term or self.term).pk,
            description=description, amount=Decimal("125.50"),
        )

    def set_term_open(self, is_open):
        self.term.is_open_for_charges = is_open
        self.term.save()

    def test_admin_can_find_create_filter_and_retry_after_term_closes(self):
        lookup = self.client.get(reverse("billing:charge_lookup"), {"school_id": self.patient.patient.school_id})
        self.assertContains(lookup, self.create_url(self.visit))
        self.assertNotContains(lookup, self.visit.chief_complaint)
        self.assertContains(self.client.get(self.create_url(self.visit)), "Create pending charge")

        Patient.objects.filter(pk=self.patient.pk).update(affiliation=Affiliation.STAFF)
        data = self.payload()
        response = self.client.post(self.create_url(self.visit), data)
        charge = StudentCharge.objects.get(charge_code=data["request_code"].hex)
        self.assertRedirects(response, self.detail_url(charge))
        self.assertEqual(charge.amount, Decimal("125.50"))
        self.assertEqual(charge.currency_code, "PHP")
        self.assertEqual(charge.status, StudentCharge.Status.PENDING)

        charges_url = reverse("billing:charges")
        listing = self.client.get(charges_url, {"term": self.term.pk, "status": "Pending"})
        self.assertContains(listing, self.detail_url(charge))
        self.assertContains(listing, f'{reverse("billing:charge_export")}?term={self.term.pk}')
        self.assertNotContains(self.client.get(charges_url, {"status": "Posted"}), charge.charge_code)

        self.set_term_open(False)
        retry = self.client.post(self.create_url(self.visit), data)
        self.assertRedirects(retry, self.detail_url(charge))
        conflicting = self.client.post(self.create_url(self.visit), {**data, "amount": "200.00"})
        self.assertContains(conflicting, "already submitted with different details")
        self.assertContains(self.client.post(self.create_url(self.visit), self.payload()), "This term is closed")
        self.assertEqual(StudentCharge.objects.count(), 1)
        self.assertEqual(self.admin.audit_events.filter(action_performed="Tuition charge created").count(), 1)

    def test_personnel_visits_have_no_charge_form_or_line(self):
        for affiliation in (Affiliation.FACULTY, Affiliation.STAFF):
            with self.subTest(affiliation=affiliation):
                self.patient.affiliation = affiliation
                self.patient.save(update_fields=["affiliation"])
                visit = MedicalRecord.objects.create(patient=self.patient, provider=self.provider)
                response = self.client.get(self.create_url(visit))
                self.assertContains(response, "Faculty and Staff visits are free.")
                self.assertNotContains(response, 'name="amount"')
                self.assertContains(self.client.post(self.create_url(visit), self.payload()), "visits are free")
        self.assertFalse(StudentCharge.objects.exists())

    def test_charge_creation_rejects_nonpositive_amount_and_free_text_description(self):
        for overrides in ({"amount": "0"}, {"amount": "-1"}, {"description": "Fictional clinical history"}):
            with self.subTest(overrides=overrides):
                response = self.client.post(self.create_url(self.visit), self.payload(**overrides))
                self.assertContains(response, "Please check your details")
        self.assertFalse(StudentCharge.objects.exists())

    def test_posting_and_reversal_require_confirmation_and_are_idempotent(self):
        charge = self.service_charge()
        url = self.detail_url(charge)
        post = {"action": "post", "post-confirm": "on"}
        void = {"action": "void", "void-confirm": "on", "void-reason": "Duplicate training entry"}

        self.assertContains(self.client.post(url, {"action": "post"}), "This field is required")
        self.set_term_open(False)
        self.assertContains(self.client.post(url, post), "This term is closed")
        charge.refresh_from_db()
        self.assertEqual(charge.status, StudentCharge.Status.PENDING)

        self.set_term_open(True)
        self.assertRedirects(self.client.post(url, post), url)
        charge.refresh_from_db()
        original_posted_at = charge.posted_at
        original_reference = f"DEMO-POST-{charge.charge_code}"
        self.assertEqual(charge.status, StudentCharge.Status.POSTED)
        self.assertEqual(charge.billing_reference, original_reference)
        self.assertContains(self.client.get(url), "Simulated posting reference")
        self.assertRedirects(self.client.post(url, post), url)
        self.assertContains(self.client.post(url, {**void, "void-expected_status": "Pending"}), "Charge status changed")

        self.set_term_open(False)
        reverse_post = {**void, "void-expected_status": "Posted"}
        self.assertContains(self.client.post(url, {**reverse_post, "void-confirm": ""}), "This field is required")
        self.assertRedirects(self.client.post(url, reverse_post), url)
        self.assertRedirects(self.client.post(url, reverse_post), url)
        charge.refresh_from_db()
        self.assertEqual(charge.status, StudentCharge.Status.VOIDED)
        self.assertEqual(charge.posted_at, original_posted_at)
        self.assertEqual(charge.billing_reference, original_reference)
        self.assertEqual(charge.reversal_reference, f"DEMO-REV-{charge.charge_code}")
        self.assertEqual(charge.amount, Decimal("125.50"))
        self.assertEqual(self.admin.audit_events.filter(action_performed="Simulated tuition posting acknowledged").count(), 1)
        self.assertEqual(self.admin.audit_events.filter(action_performed="Simulated tuition reversal confirmed").count(), 1)

    def test_draft_charge_cannot_post_and_can_be_voided_without_a_reversal(self):
        draft = MedicalRecord.objects.create(patient=self.patient, provider=self.provider)
        charge = self.service_charge(visit=draft)
        url = self.detail_url(charge)
        self.assertNotContains(self.client.get(url), "Record simulated posting")
        response = self.client.post(url, {"action": "post", "post-confirm": "on"})
        self.assertContains(response, "Finalize the encounter")
        self.assertRedirects(self.client.post(url, {
            "action": "void", "void-expected_status": "Pending", "void-confirm": "on", "void-reason": "Correction",
        }), url)
        charge.refresh_from_db()
        self.assertEqual(charge.status, StudentCharge.Status.VOIDED)
        self.assertIsNone(charge.posted_at)
        self.assertIsNone(charge.reversal_reference)

    def test_pending_csv_is_term_scoped_and_preserves_status(self):
        charge = self.service_charge(description=" ＋2\nFictional")
        posted = self.service_charge()
        self.client.post(self.detail_url(posted), {"action": "post", "post-confirm": "on"})
        other_term = AcademicTerm.objects.create(
            academic_year="2026-2027", semester="Second", start_date=date(2027, 1, 1),
            end_date=date(2027, 5, 1), is_open_for_charges=True,
        )
        other = self.service_charge(term=other_term)
        audit_count = self.admin.audit_events.count()

        url = reverse("billing:charge_export")
        response = self.client.get(url, {"term": self.term.pk, "status": "Posted"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("no-store", response["Cache-Control"])
        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))
        self.assertEqual(rows, [
            ["charge_code", "student_id", "academic_year", "semester", "description", "amount", "currency"],
            [charge.charge_code, self.patient.patient.school_id, "2026-2027", "First", "Text: ＋2 Fictional", "125.50", "PHP"],
        ])
        self.assertNotContains(response, self.visit.chief_complaint)
        self.assertContains(self.client.get(url), other.charge_code)
        self.assertEqual(self.client.get(url, {"term": "invalid"}).status_code, 400)
        charge.refresh_from_db()
        self.assertEqual(charge.status, StudentCharge.Status.PENDING)
        self.assertEqual(self.admin.audit_events.count(), audit_count)

    def test_patient_detail_is_owned_and_read_only(self):
        charge = self.service_charge()
        self.client.post(self.detail_url(charge), {
            "action": "void", "void-expected_status": "Pending", "void-confirm": "on",
            "void-reason": "Internal reconciliation note",
        })
        list_url = reverse("billing:patient_charges")
        detail_url = reverse("billing:patient_charge_detail", args=[charge.pk])
        self.client.force_login(self.patient.patient)
        self.assertContains(self.client.get(reverse("home:home")), list_url)
        self.assertContains(self.client.get(list_url), detail_url)
        detail = self.client.get(detail_url)
        self.assertContains(detail, "Voided")
        self.assertNotContains(detail, "Internal reconciliation note")
        self.assertNotContains(detail, "Void charge")
        self.assertEqual(self.client.post(detail_url).status_code, 405)
        for url in (reverse("billing:charges"), reverse("billing:charge_export"), self.detail_url(charge)):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(self.create_url(self.visit), self.payload()).status_code, 403)

        other_user = User.objects.create_user("TEST-OTHER", "other@example.invalid", "test-password")
        Patient.objects.create(patient=other_user, affiliation=Affiliation.STUDENT)
        self.client.force_login(other_user)
        self.assertNotContains(self.client.get(list_url), charge.charge_code)
        self.assertEqual(self.client.get(detail_url).status_code, 404)

    def test_database_preserves_pending_line_and_rejects_fabricated_void_metadata(self):
        charge = self.service_charge()
        rows = StudentCharge.objects.filter(pk=charge.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            rows.update(amount=Decimal("250.00"))
        now = timezone.now()
        with self.assertRaises(IntegrityError), transaction.atomic():
            rows.update(status="Voided", posted_at=now, voided_at=now, billing_reference="TEST-POST",
                reversal_reference="TEST-REV", void_reason="Correction")
        charge.refresh_from_db()
        self.assertEqual(charge.amount, Decimal("125.50"))
        self.assertEqual(charge.status, StudentCharge.Status.PENDING)
