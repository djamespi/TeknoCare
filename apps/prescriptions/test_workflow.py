from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections, IntegrityError, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.clinical.consultation import consultation_version, finalize_consultation
from apps.clinical.models import MedicalRecord
from apps.clinical.reception import assign_encounter
from apps.common.test_data import clinic_data
from apps.patients.models import Patient
from apps.providers.models import Provider
from apps.register.models import User

from .models import Medication, Prescription, PrescriptionItem
from .services import discard_or_cancel, issue_prescription, prescription_version, save_item, start_prescription, start_replacement


class PrescriptionWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.doctor, _, _ = clinic_data()
        cls.visit = MedicalRecord.objects.create(patient=cls.patient, provider=cls.doctor,
            chief_complaint="Fictional complaint", symptoms="Fictional symptoms", treatment_plan="Fictional plan")
        cls.medication = Medication.objects.create(medication_code="DEMO", generic_name="Fictional medicine",
            strength="Demo strength", dosage_form="Demo form")
        nurse_account = User.objects.create_user("RX-NURSE", "rx-nurse@example.invalid", user_type="Provider")
        cls.nurse = Provider.objects.create(provider=nurse_account, is_active=True, provider_type="Nurse")
        other_account = User.objects.create_user("RX-DENTIST", "rx-dentist@example.invalid", user_type="Provider")
        cls.dentist = Provider.objects.create(provider=other_account, is_active=True, provider_type="Dentist")
        cls.other_patient = Patient.objects.create(patient=User.objects.create_user(
            "RX-OTHER", "rx-other@example.invalid",
        ), affiliation="Student")
        cls.values = {"dose": "Demo dose", "route": "Demo route", "frequency": "Demo schedule",
            "duration_days": 1, "quantity": "1.00", "quantity_unit": "Demo unit", "instructions": "Fictional instructions"}

    def draft(self):
        return start_prescription(actor=self.doctor.provider, record_id=self.visit.pk)

    def test_formulary_is_read_only_and_limited_to_active_clinicians(self):
        url = reverse("prescriptions:formulary")
        self.client.force_login(self.patient.patient)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.nurse.provider)
        response = self.client.get(url, {"q": self.medication.dosage_form})
        self.assertContains(response, self.medication.generic_name)
        self.assertEqual(response.context["totals"]["active"], 1)
        self.assertNotContains(response, reverse("prescriptions:medication_edit", args=[self.medication.pk]))
        self.assertEqual(self.client.post(url).status_code, 405)
        self.nurse.is_active = False
        self.nurse.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(url).status_code, 403)

    def version(self, prescription):
        prescription.refresh_from_db()
        return prescription_version(prescription, prescription.items.all())

    def arguments(self, prescription):
        return {"actor": self.doctor.provider, "record_id": prescription.record_id,
            "prescription_id": prescription.pk, "expected_version": self.version(prescription)}

    def add(self, prescription):
        save_item(**self.arguments(prescription), medication_id=self.medication.pk, values=self.values)
        return prescription.items.get()

    def detail(self, prescription):
        return reverse("prescriptions:detail", args=[prescription.record_id, prescription.pk])

    def finalize(self):
        self.visit.refresh_from_db()
        finalize_consultation(actor=self.doctor.provider, record_id=self.visit.pk,
            expected_version=consultation_version(self.visit, (), None))

    def test_attending_uses_web_flow_and_patient_only_sees_published_history(self):
        encounter = reverse("prescriptions:encounter", args=[self.visit.pk])
        self.client.force_login(self.doctor.provider)
        self.assertContains(self.client.get(encounter), "Start prescription draft")
        response = self.client.post(encounter, {"prescriber": self.nurse.pk}, follow=True)
        self.assertContains(response, "Add medication item")
        prescription = self.visit.prescriptions.get()
        self.assertEqual(prescription.prescriber_id, self.doctor.pk)
        detail = self.detail(prescription)
        issue = {"action": "issue", "issue-confirm": "on", "issue-expected_version": self.version(prescription)}
        self.assertContains(self.client.post(detail, issue), "Add at least one medicine")
        patient_client = Client()
        patient_client.force_login(self.patient.patient)
        history = reverse("prescriptions:history")
        printed = reverse("prescriptions:print", args=[prescription.pk])
        self.assertNotContains(patient_client.get(history), printed)
        self.assertEqual(patient_client.get(printed).status_code, 404)
        add_url = reverse("prescriptions:item_create", args=[self.visit.pk, prescription.pk])
        data = {**self.values, "medication": self.medication.pk, "expected_version": self.version(prescription)}
        self.assertContains(self.client.post(add_url, {**data, "quantity": "0"}), "greater than or equal to 0.01")
        self.assertRedirects(self.client.post(add_url, data), detail)
        issue["issue-expected_version"] = self.version(prescription)
        self.assertRedirects(self.client.post(detail, issue), detail)
        prescription.refresh_from_db()
        self.assertEqual(prescription.status, "Issued")
        self.assertIsNotNone(prescription.issued_at)
        self.assertEqual(self.client.get(add_url).status_code, 403)
        self.assertContains(patient_client.get(history), printed)
        response = patient_client.get(printed)
        self.assertContains(response, "Invalid for dispensing")
        self.assertContains(response, "Demo schedule")
        self.assertNotContains(response, self.visit.chief_complaint)
        patient_client.force_login(self.other_patient.patient)
        self.assertNotContains(patient_client.get(history), printed)
        self.assertEqual(patient_client.get(printed).status_code, 404)

    def test_others_cannot_prescribe_and_posts_require_csrf(self):
        visit_url = reverse("prescriptions:encounter", args=[self.visit.pk])
        for account, status in ((self.nurse.provider, 404), (self.dentist.provider, 404),
            (self.patient.patient, 403), (self.admin, 403)):
            self.client.force_login(account)
            self.assertEqual(self.client.post(visit_url).status_code, status)
            with self.assertRaises(PermissionDenied):
                start_prescription(actor=account, record_id=self.visit.pk)
        secured = Client(enforce_csrf_checks=True)
        secured.force_login(self.doctor.provider)
        self.assertEqual(secured.post(visit_url).status_code, 403)

    def test_catalog_edit_scope_and_activity(self):
        catalog = reverse("prescriptions:catalog")
        self.client.force_login(self.doctor.provider)
        self.assertEqual(self.client.get(catalog).status_code, 403)
        self.client.force_login(self.admin)
        values = {"medication_code": "NEW", "generic_name": "Fictional medicine", "strength": "Draft strength",
            "dosage_form": "Demo form", "is_active": "on"}
        self.assertRedirects(self.client.post(reverse("prescriptions:medication_create"), values), catalog)
        medication = Medication.objects.get(medication_code="NEW")
        self.assertRedirects(self.client.post(reverse("prescriptions:medication_edit", args=[medication.pk]),
            {**values, "strength": "Revised strength"}), catalog)
        self.assertContains(self.client.get(catalog), "Revised strength")

    def test_stale_draft_review_and_inactive_item_block_issue(self):
        prescription = self.draft()
        stale = self.arguments(prescription)
        self.add(prescription)
        with self.assertRaisesMessage(ValidationError, "changed"):
            issue_prescription(**stale)
        Medication.objects.filter(pk=self.medication.pk).update(is_active=False)
        with self.assertRaisesMessage(ValidationError, "inactive medications"):
            issue_prescription(**self.arguments(prescription))
        self.assertEqual(prescription.status, "Draft")

    def test_finalization_blocks_drafts_and_discard_is_private(self):
        prescription = self.draft()
        with self.assertRaisesMessage(ValidationError, "Resolve the existing"):
            self.draft()
        with self.assertRaisesMessage(ValidationError, "before finalizing"):
            self.finalize()
        discard_or_cancel(**self.arguments(prescription))
        self.finalize()
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, "Finalized")
        self.client.force_login(self.patient.patient)
        self.assertEqual(self.client.get(reverse("prescriptions:print", args=[prescription.pk])).status_code, 404)

    def test_correction_after_finalization_keeps_old_copy_and_audits_replacement(self):
        prescription = self.draft()
        self.add(prescription)
        issue_prescription(**self.arguments(prescription))
        self.finalize()
        discard_or_cancel(**self.arguments(prescription))
        prescription.refresh_from_db()
        self.assertEqual(prescription.status, "Canceled")
        self.assertIsNotNone(prescription.issued_at)
        self.assertEqual(prescription.items.get().dose, self.values["dose"])
        followup = MedicalRecord.objects.create(patient=self.patient, provider=self.doctor)
        replacement = start_replacement(actor=self.doctor.provider, record_id=followup.pk, old_prescription_id=prescription.pk)
        self.assertEqual((replacement.status, replacement.record_id), ("Draft", followup.pk))
        another = MedicalRecord.objects.create(patient=self.patient, provider=self.doctor)
        with self.assertRaisesMessage(ValidationError, "already been started"):
            start_replacement(actor=self.doctor.provider, record_id=another.pk, old_prescription_id=prescription.pk)
        self.assertTrue(AuditLog.objects.filter(target_record_id=replacement.pk, target_table="prescription",
            action_performed=f"Replacement draft for prescription #{prescription.pk}").exists())
        self.client.force_login(self.patient.patient)
        self.assertContains(self.client.get(reverse("prescriptions:print", args=[prescription.pk])), "Canceled prescription")
        self.assertEqual(self.client.get(reverse("prescriptions:print", args=[replacement.pk])).status_code, 404)

    def test_reassignment_allows_discard_but_never_changes_draft_authorship(self):
        prescription = self.draft()
        self.add(prescription)
        assign_encounter(actor=self.admin, record_id=self.visit.pk, provider_id=self.dentist.pk, expected_provider_id=self.doctor.pk)
        with self.assertRaises(PermissionDenied):
            issue_prescription(**self.arguments(prescription))
        arguments = {**self.arguments(prescription), "actor": self.dentist.provider}
        with self.assertRaisesMessage(ValidationError, "your own"):
            issue_prescription(**arguments)
        discard_or_cancel(**arguments)
        prescription.refresh_from_db()
        self.assertEqual((prescription.status, prescription.prescriber_id), ("Canceled", self.doctor.pk))

    def test_database_rejects_bypass_and_keeps_canceled_items_and_formulation(self):
        prescription = self.draft()
        rejected = (
            lambda: Prescription.objects.filter(pk=prescription.pk).update(status="Issued", issued_at=timezone.now()),
            lambda: Prescription.objects.bulk_create([Prescription(record=self.visit, prescriber=self.doctor)]),
            lambda: MedicalRecord.objects.filter(pk=self.visit.pk).update(status="Finalized", finalized_at=timezone.now()),
        )
        for action in rejected:
            with self.assertRaises(IntegrityError), transaction.atomic():
                action()
        item = self.add(prescription)
        issue_prescription(**self.arguments(prescription))
        discard_or_cancel(**self.arguments(prescription))
        rejected = (
            lambda: PrescriptionItem.objects.filter(pk=item.pk).update(dose="Rewritten"),
            lambda: PrescriptionItem.objects.filter(pk=item.pk).delete(),
            lambda: PrescriptionItem.objects.bulk_create([PrescriptionItem(prescription=prescription,
                medication=self.medication, **self.values)]),
            lambda: Prescription.objects.filter(pk=prescription.pk).update(issued_at=None),
            lambda: Medication.objects.filter(pk=self.medication.pk).update(strength="Rewritten"),
        )
        for action in rejected:
            with self.assertRaises(IntegrityError), transaction.atomic():
                action()
        Medication.objects.filter(pk=self.medication.pk).update(is_active=False)
        item.refresh_from_db()
        self.assertEqual((item.dose, item.medication.strength), ("Demo dose", "Demo strength"))


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class PrescriptionConcurrencyTests(TransactionTestCase):
    available_apps = settings.INSTALLED_APPS

    def test_two_issue_requests_publish_only_once(self):
        _, patient, doctor, _, _ = clinic_data()
        visit = MedicalRecord.objects.create(patient=patient, provider=doctor)
        prescription = start_prescription(actor=doctor.provider, record_id=visit.pk)
        medication = Medication.objects.create(medication_code="RACE", generic_name="Fictional medicine",
            strength="Demo strength", dosage_form="Demo form")
        arguments = {"actor": doctor.provider, "record_id": visit.pk, "prescription_id": prescription.pk}
        save_item(**arguments, expected_version=prescription_version(prescription, ()), medication_id=medication.pk,
            values={"dose": "Demo dose", "route": "Demo route", "frequency": "Demo schedule", "duration_days": 1,
                "quantity": "1.00", "quantity_unit": "Demo unit"})
        version = prescription_version(prescription, prescription.items.all())
        gate = Barrier(2, timeout=10)

        def attempt(_):
            close_old_connections()
            try:
                gate.wait()
                issue_prescription(**arguments, expected_version=version)
                return "issued"
            except ValidationError as error:
                self.assertIn("changed", str(error))
                return "stale"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(list(executor.map(attempt, range(2), timeout=20)), ["issued", "stale"])
        self.assertEqual(AuditLog.objects.filter(target_table="prescription", target_record_id=prescription.pk,
            action_performed="Prescription issued").count(), 1)
