"""Fictional fixtures shared only by the feature test suites."""
from datetime import timedelta
from django.utils import timezone
from apps.register.models import User
from apps.patients.models import Affiliation, Patient
from apps.providers.models import Provider
from apps.appointments.models import ClinicRoom, Slot
from apps.clinical.models import MedicalRecord


def clinic_data():
    admin = User.objects.create_superuser("TEST-ADMIN", "admin@example.invalid", "test-password")
    user = User.objects.create_user("TEST-STUDENT", "student@example.invalid", "test-password", fname="Test", lname="Student")
    patient = Patient.objects.create(patient=user, affiliation=Affiliation.STUDENT)
    doctor = User.objects.create_user("TEST-DOCTOR", "doctor@example.invalid", "test-password", user_type="Provider", fname="Test", lname="Doctor")
    provider = Provider.objects.create(provider=doctor, provider_type=Provider.Type.PHYSICIAN, is_active=True)
    room = ClinicRoom.objects.create(campus="Fictional", building="Test", room_number="101")
    now = timezone.now()
    slot = Slot.objects.create(provider=provider, room=room, start_time=now + timedelta(days=1), end_time=now + timedelta(days=1, minutes=30), is_active=True)
    record = MedicalRecord.objects.create(patient=patient, provider=provider, chief_complaint="Fictional test visit", visited_at=now,
        status=MedicalRecord.Status.FINALIZED, finalized_at=now)
    return admin, patient, provider, slot, record
