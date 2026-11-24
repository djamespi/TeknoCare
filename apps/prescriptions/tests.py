from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from apps.common.test_data import clinic_data
from apps.clinical.models import MedicalRecord
from .models import Medication, Prescription, PrescriptionItem


class PrescriptionModelTests(TestCase):
    def setUp(self):
        _, patient, provider, _, _ = clinic_data()
        record = MedicalRecord.objects.create(patient=patient, provider=provider)
        self.prescription = Prescription.objects.create(record=record, prescriber=provider)
        self.medication = Medication.objects.create(medication_code="TEST", generic_name="Fictional medicine", strength="Test strength", dosage_form="Test form")

    def test_cannot_issue_without_items(self):
        self.prescription.status = "Issued"; self.prescription.issued_at = timezone.now()
        with self.assertRaises(ValidationError): self.prescription.save()

    def test_issued_items_and_catalog_formulation_are_preserved(self):
        item = PrescriptionItem.objects.create(prescription=self.prescription, medication=self.medication, dose="Test dose", route="Test route", frequency="Test schedule", duration_days=1, quantity="1.00", quantity_unit="Test unit")
        self.prescription.status = "Issued"; self.prescription.issued_at = timezone.now(); self.prescription.save()
        item.dose = "Changed"
        with self.assertRaises(ValidationError): item.save()
        self.medication.strength = "Changed"
        with self.assertRaises(ValidationError): self.medication.save()
