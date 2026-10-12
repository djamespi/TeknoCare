"""Fictional activity records, using TeknoCare's existing clinic models."""

from datetime import datetime, timedelta, timezone

from django.contrib.auth.hashers import make_password
from django.core.management.base import CommandError
from django.db import transaction

from apps.register.models import Appointment, Patient, Provider, Slot, User


PATIENT_SAMPLES = (
    ("JOIN-DEMO-001", "Ana", "Reyes", "ana@join-demo.example.invalid"),
    ("JOIN-DEMO-002", "Ben", "Santos", "ben@join-demo.example.invalid"),
    ("JOIN-DEMO-003", "Carlo", "Lim", "carlo@join-demo.example.invalid"),
)
PROVIDER_SAMPLE = ("JOIN-DEMO-004", "Maya", "Cruz", "maya@join-demo.example.invalid")
APPOINTMENT_SAMPLES = (
    (0, "Routine check-up", Appointment.Status.SCHEDULED),
    (0, "Follow-up consultation", Appointment.Status.COMPLETED),
    (1, "Health clearance", Appointment.Status.SCHEDULED),
)


def _sample_user(sample, user_type):
    school_id, fname, lname, email = sample
    expected = {
        "fname": fname,
        "lname": lname,
        "email": email,
        "user_type": user_type,
        "account_status": User.AccountStatus.SUSPENDED,
    }
    user, created = User.objects.get_or_create(
        school_id=school_id,
        defaults={**expected, "password_hash": make_password(None)},
    )
    if not created and any(getattr(user, field) != value for field, value in expected.items()):
        raise CommandError(
            f"Reserved sample ID {school_id} already has different data. "
            "No existing account will be overwritten."
        )
    return user


def _sample_record(model, lookup, expected):
    record, created = model.objects.get_or_create(**lookup, defaults=expected)
    if not created and any(getattr(record, field) != value for field, value in expected.items()):
        raise CommandError(
            f"An existing {model.__name__} sample has different data. "
            "No existing record will be overwritten."
        )
    return record


@transaction.atomic
def seed_demo_data():
    """Add missing samples, reuse identical ones, and roll back on conflicts.

    No records are deleted. Samples cannot sign in and use reserved fake emails.
    Database IDs are assigned normally, so existing primary keys are preserved.
    """
    patients = []
    for sample in PATIENT_SAMPLES:
        user = _sample_user(sample, User.UserType.PATIENT)
        patients.append(_sample_record(Patient, {"patient": user}, {
            "emergency_contact": "Fictional SQL JOIN activity contact",
            "medical_history_summary": "Fictional learning record; no real medical data.",
            "no_show_count": 0,
        }))

    provider_user = _sample_user(PROVIDER_SAMPLE, User.UserType.PROVIDER)
    provider = _sample_record(Provider, {"provider": provider_user}, {
        "specialization": "General Medicine",
        "room_number": "DEMO-101",
        "is_active": False,
    })
    first_start = datetime(2026, 10, 13, 9, 0, tzinfo=timezone.utc)
    appointments = []
    for index, (patient_index, reason, status) in enumerate(APPOINTMENT_SAMPLES):
        start = first_start + timedelta(hours=index)
        slot = _sample_record(Slot, {"provider": provider, "start_time": start}, {
            "end_time": start + timedelta(minutes=30),
            "is_booked": True,
        })
        appointments.append(_sample_record(Appointment, {"slot": slot}, {
            "patient": patients[patient_index],
            "provider": provider,
            "reason_for_visit": reason,
            "status": status,
        }))

    # Extra appointments would change the intended 2/1/0 learning dataset.
    actual_ids = set(Appointment.objects.filter(patient__in=patients).values_list("pk", flat=True))
    if actual_ids != {appointment.pk for appointment in appointments}:
        raise CommandError("The sample patients have extra appointments. No records were deleted; setup rolled back.")
    return patients, appointments
