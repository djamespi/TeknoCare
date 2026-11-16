from datetime import timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from apps.register.models import User
from .models import EmergencyContact, Patient


class PatientModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("PATIENT-TEST", "patient@example.invalid", "test-password")

    def test_new_patient_requires_verified_affiliation(self):
        with self.assertRaises(ValidationError): Patient.objects.create(patient=self.user)

    def test_future_birth_date_rejected(self):
        with self.assertRaises(ValidationError):
            Patient.objects.create(patient=self.user, affiliation="Student", date_of_birth=timezone.localdate() + timedelta(days=1))

    def test_only_one_primary_contact_per_patient(self):
        patient = Patient.objects.create(patient=self.user, affiliation="Student")
        EmergencyContact.objects.create(patient=patient, full_name="Fictional One", relationship="Parent", phone_number="0000000001", is_primary=True)
        with self.assertRaises(ValidationError):
            EmergencyContact.objects.create(patient=patient, full_name="Fictional Two", relationship="Parent", phone_number="0000000002", is_primary=True)
