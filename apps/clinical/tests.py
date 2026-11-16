from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from apps.common.test_data import clinic_data
from apps.patients.models import Patient
from .models import Diagnosis, MedicalRecord, RecordDiagnosis, VitalSign


class ClinicalModelTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()

    def test_walk_in_has_no_appointment_and_snapshots_affiliation(self):
        self.assertIsNone(self.record.appointment_id)
        self.assertEqual(self.record.affiliation_at_visit, "Student")

    def test_provider_can_also_receive_free_personnel_care(self):
        personnel = Patient.objects.create(patient=self.provider.provider, affiliation="Staff")
        visit = MedicalRecord.objects.create(patient=personnel, provider=self.provider, chief_complaint="Fictional staff visit", affiliation_at_visit="Student")
        self.assertEqual(visit.affiliation_at_visit, "Staff")

    def test_finalized_record_protected_from_bulk_overwrite(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalRecord.objects.filter(pk=self.record.pk).update(symptoms="Overwrite")

    def test_vitals_require_measurement_and_complete_bp(self):
        for values in ({}, {"systolic_mmhg": 120}, {"oxygen_saturation_pct": 101}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                VitalSign.objects.create(record=self.record, recorded_by_user=self.admin, **values)
        vital = VitalSign.objects.create(record=self.record, recorded_by_user=self.admin, temperature_c="36.5")
        self.assertIsNotNone(vital.pk)

    def test_diagnoses_unique_per_system_and_visit(self):
        first = Diagnosis.objects.create(code="TEST", coding_system="Local", description="Fictional")
        Diagnosis.objects.create(code="TEST", coding_system="Other", description="Fictional")
        RecordDiagnosis.objects.create(record=self.record, diagnosis=first, is_primary=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RecordDiagnosis.objects.bulk_create([RecordDiagnosis(record=self.record, diagnosis=first)])

    def test_clinical_history_prevents_patient_deletion(self):
        with self.assertRaises(ProtectedError):
            self.patient.delete()
