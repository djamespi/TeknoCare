from django.test import TestCase
from django.urls import reverse

from apps.appointments.models import Appointment
from apps.clinical.consultation import consultation_version, finalize_consultation
from apps.clinical.models import Diagnosis, MedicalRecord, RecordDiagnosis
from apps.clinical.referrals import create_referral
from apps.common.test_data import clinic_data
from apps.prescriptions.models import Medication
from apps.prescriptions.services import discard_or_cancel, issue_prescription, prescription_version, save_item, start_prescription
from apps.register.models import User

from .models import Patient


class PatientSummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.doctor, slot, cls.walk_in = clinic_data()
        appointment = Appointment.objects.create(
            patient=cls.patient, slot=slot, status=Appointment.Status.CHECKED_IN, reason_for_visit="Internal scheduling reason",
        )
        cls.visit = MedicalRecord.objects.create(patient=cls.patient, provider=cls.doctor, appointment=appointment,
            chief_complaint="Patient-visible reason", symptoms="Internal symptoms marker",
            examination_notes="Internal examination marker", treatment_plan="Internal treatment plan marker")
        cls.draft = MedicalRecord.objects.create(patient=cls.patient, provider=cls.doctor, chief_complaint="Private draft marker")
        account = User.objects.create_user("SUMMARY-OTHER", "summary-other@example.invalid", user_type="Patient")
        cls.other_patient = Patient.objects.create(patient=account, affiliation="Student")
        cls.referral = create_referral(actor=cls.doctor.provider, record_id=cls.visit.pk,
            destination="Fictional follow-up clinic", reason="Patient-facing referral instructions.")
        cls.draft_referral = create_referral(actor=cls.doctor.provider, record_id=cls.draft.pk,
            destination="Private draft destination", reason="Private draft referral marker")
        diagnosis = Diagnosis.objects.create(code="DEMO", coding_system="Prototype", description="Patient-visible diagnosis")
        link = RecordDiagnosis.objects.create(record=cls.visit, diagnosis=diagnosis, is_primary=True, notes="Internal diagnosis marker")
        medication = Medication.objects.create(medication_code="SUMMARY", generic_name="Fictional medication",
            dosage_form="Demo form", strength="Demo strength")
        for dose, canceled in (("Canceled medication marker", True), ("Patient-visible dose", False)):
            prescription = start_prescription(actor=cls.doctor.provider, record_id=cls.visit.pk)
            arguments = {"actor": cls.doctor.provider, "record_id": cls.visit.pk, "prescription_id": prescription.pk}
            save_item(**arguments, expected_version=prescription_version(prescription, ()), medication_id=medication.pk, values={
                "dose": dose, "route": "Demo route", "frequency": "Demo schedule", "duration_days": 1,
                "quantity": "1.00", "quantity_unit": "Demo unit", "instructions": "Patient-facing medication instructions.",
            })
            issue_prescription(**arguments, expected_version=prescription_version(prescription, prescription.items.all()))
            if canceled:
                prescription.refresh_from_db()
                discard_or_cancel(**arguments, expected_version=prescription_version(prescription, prescription.items.all()))
            else:
                cls.prescription = prescription
        finalize_consultation(actor=cls.doctor.provider, record_id=cls.visit.pk,
            expected_version=consultation_version(cls.visit, (link,), None))

    def test_list_and_print_return_only_patient_facing_content(self):
        self.client.force_login(self.patient.patient)
        listing = self.client.get(reverse("patients:visits"))
        self.assertContains(listing, reverse("patients:visit_summary", args=[self.visit.pk]))
        self.assertContains(listing, reverse("patients:visit_summary", args=[self.walk_in.pk]))
        self.assertNotContains(listing, "Private draft marker")
        for name in ("visit_summary", "visit_print"):
            with self.subTest(page=name):
                response = self.client.get(reverse(f"patients:{name}", args=[self.visit.pk]))
                for visible in ("Scheduled", "Patient-visible reason", "Patient-visible diagnosis", "Patient-visible dose",
                    "Patient-facing medication instructions.", "Patient-facing referral instructions.",
                    reverse("prescriptions:print", args=[self.prescription.pk])):
                    self.assertContains(response, visible)
                for private in ("Internal symptoms marker", "Internal examination marker", "Internal treatment plan marker",
                    "Internal diagnosis marker", "Internal scheduling reason", "Canceled medication marker", "Private draft"):
                    self.assertNotContains(response, private)
                self.assertIn("no-store", response.headers["Cache-Control"])

    def test_walk_in_summary_without_optional_entries_renders_empty_sections(self):
        self.client.force_login(self.patient.patient)
        response = self.client.get(reverse("patients:visit_summary", args=[self.walk_in.pk]))
        for text in ("Walk-in", "No diagnoses recorded", "No current issued prescriptions", "No referrals recorded"):
            self.assertContains(response, text)

    def test_patient_cannot_read_drafts_or_another_patients_print_views(self):
        self.client.force_login(self.patient.patient)
        for name in ("visit_summary", "visit_print"):
            self.assertEqual(self.client.get(reverse(f"patients:{name}", args=[self.draft.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("patients:referral_print", args=[self.draft.pk, self.draft_referral.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("patients:referral_print", args=[self.visit.pk, self.draft_referral.pk])).status_code, 404)
        self.client.force_login(self.other_patient.patient)
        self.assertNotContains(self.client.get(reverse("patients:visits")), "Patient-visible reason")
        for name in ("visit_summary", "visit_print"):
            self.assertEqual(self.client.get(reverse(f"patients:{name}", args=[self.visit.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("patients:referral_print", args=[self.visit.pk, self.referral.pk])).status_code, 404)

    def test_referral_print_is_read_only_and_shows_canceled_history(self):
        self.client.force_login(self.patient.patient)
        url = reverse("patients:referral_print", args=[self.visit.pk, self.referral.pk])
        self.assertEqual(self.client.post(url, {"status": "Completed"}).status_code, 405)
        self.referral.refresh_from_db()
        self.assertEqual(self.referral.status, "Pending")
        self.referral.status = "Canceled"
        self.referral.save(update_fields=["status"])
        response = self.client.get(url)
        self.assertContains(response, "prototype referral copy")
        self.assertContains(response, "Canceled referral")
        self.assertContains(response, "Patient-facing referral instructions.")
        self.assertNotContains(response, "Save follow-up")
