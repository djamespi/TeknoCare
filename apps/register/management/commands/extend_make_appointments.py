"""Add fictional patients and a schedule to the dedicated Make sample database."""
from datetime import datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from apps.appointments.models import Appointment, Slot
from apps.appointments.services import book_appointment, save_room
from apps.audit.models import AuditLog
from apps.clinical.models import MedicalRecord
from apps.patients.models import Affiliation, Patient
from apps.providers.models import Provider
from apps.providers.services import save_provider
from apps.register.models import User
from apps.register.services import create_patient_account, create_provider_account
from apps.university.models import Department


BATCH_ACTION = "Added Filipino clinic booking sample"
PATIENTS = (
    ("23-10481", "Bianca", "Manalaysay", Affiliation.STUDENT, "CCS"),
    ("24-10532", "Miguel", "Abadiano", Affiliation.STUDENT, "CEA"),
    ("24-10647", "Katrina", "Montecillo", Affiliation.STUDENT, "CNAHS"),
    ("25-10358", "Paolo", "Lumapas", Affiliation.STUDENT, "CMBA"),
    ("FAC-1028", "Lorna", "Dimalanta", Affiliation.FACULTY, "CASE"),
    ("STF-1042", "Ramon", "Caballero", Affiliation.STAFF, "HRD"),
)
PROVIDERS = (
    ("MD-1048", "Mara", "Villareal", Provider.Type.PHYSICIAN, "Campus Health Consultations", "HSC-103"),
    ("RN-2073", "Joel", "Macaraeg", Provider.Type.NURSE, "Nursing and Wellness", "HSC-104"),
)


def sample_email(first_name, last_name):
    return f"{first_name.lower()}.{last_name.lower()}@example.invalid"


def slot_at(provider, room, day, hour, minute=0):
    start = timezone.make_aware(datetime.combine(day, time(hour, minute)))
    return Slot(provider=provider, room=room, start_time=start,
                end_time=start + timedelta(minutes=30), is_active=True)


def add_bookings(patients, care_teams):
    today = timezone.localdate()
    # Leave regular morning and afternoon availability after the seeded bookings.
    days = [today + timedelta(days=offset) for offset in range(1, 29)]
    weekdays = [day for day in days if day.weekday() in (1, 2, 3)]
    upcoming = [slot_at(provider, room, day, hour) for day in weekdays
                for provider, room in care_teams for hour in (9, 14)]
    Slot.objects.bulk_create(upcoming)

    reasons = ("General clinic consultation", "Wellness check", "Campus health clearance consultation",
               "Blood pressure screening", "Routine follow-up", "Nursing assessment")
    # Each patient gets an upcoming morning visit. Alternate between the two providers.
    morning_slots = [slot for slot in upcoming if timezone.localtime(slot.start_time).hour == 9]
    for patient, reason, slot in zip(patients, reasons, morning_slots[:len(patients)], strict=True):
        book_appointment(patient_id=patient.pk, slot_id=slot.pk, reason_for_visit=reason,
                         actor=patient.patient, expected_version=slot.version)

    past_days = [today - timedelta(days=offset) for offset in range(4, 21)]
    past_weekdays = [day for day in past_days if day.weekday() in (1, 2, 3)]
    statuses = (Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW, Appointment.Status.COMPLETED,
                Appointment.Status.CANCELED, Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW)
    historical = []
    for index, day in enumerate(past_weekdays[:len(statuses)]):
        # Completed encounters belong to the physician.
        provider, room = care_teams[index % 2]
        historical.append(slot_at(provider, room, day, 10, 30))
    Slot.objects.bulk_create(historical)
    for patient, reason, status, slot in zip(patients, reasons, statuses, historical, strict=True):
        appointment = Appointment.objects.create(
            patient=patient, slot=slot, reason_for_visit=reason, status=status,
            created_at=slot.start_time - timedelta(days=3),
            canceled_at=slot.start_time - timedelta(days=1) if status == Appointment.Status.CANCELED else None,
        )
        if status == Appointment.Status.COMPLETED:
            MedicalRecord.objects.create(
                appointment=appointment, patient=patient, provider=slot.provider, chief_complaint=reason,
                status=MedicalRecord.Status.FINALIZED, visited_at=slot.start_time, finalized_at=slot.end_time,
            )
    return len(historical) + len(patients), len(upcoming) - len(patients)


class Command(BaseCommand):
    help = "Add fictional Filipino patients, providers and appointments to the dedicated Make sample database."

    def add_arguments(self, parser):
        parser.add_argument("--credentials-file", type=Path, default=settings.BASE_DIR / "tmp/make-demo-password.txt",
                            help="Private file containing the sample account password.")

    @transaction.atomic
    def handle(self, credentials_file, **options):
        if not getattr(settings, "TEKNOCARE_MAKE_DEMO", False) or connection.vendor != "postgresql":
            raise CommandError("Use the dedicated Make sample database for this command.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            if cursor.fetchone()[0] != "teknocare_make_demo":
                raise CommandError("The connection is not the dedicated Make sample database.")
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", (790441359,))
        if AuditLog.objects.filter(action_performed=BATCH_ACTION, target_table="system").exists():
            self.stdout.write("This appointment sample has already been added.")
            return

        try:
            password = credentials_file.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as error:
            raise CommandError("The sample credentials file could not be read.") from error
        if len(password) < 16:
            raise CommandError("Set a sample password of at least 16 characters in the private credentials file.")

        identities = PATIENTS + PROVIDERS
        school_ids = [row[0] for row in identities]
        emails = [sample_email(row[1], row[2]) for row in identities]
        if User.objects.filter(Q(school_id__in=school_ids) | Q(email__in=emails)).exists():
            raise CommandError("One of the sample account identities is already in use.")
        admin = User.objects.filter(school_id="ADM-0001", user_type=User.UserType.ADMIN,
                                    account_status=User.AccountStatus.ACTIVE).first()
        if admin is None:
            raise CommandError("Import the original Make sample with an active sample administrator first.")
        departments = Department.objects.filter(is_active=True).in_bulk(field_name="code")
        if any(code not in departments for *_, code in PATIENTS):
            raise CommandError("The original sample departments must be active to add the new patients.")

        patients = []
        for school_id, first, last, affiliation, code in PATIENTS:
            user = create_patient_account(actor=admin, school_id=school_id, email=sample_email(first, last),
                                          first_name=first, last_name=last, password=password,
                                          affiliation=affiliation, department=departments[code])
            patients.append(user.patient_profile)

        care_teams = []
        for school_id, first, last, designation, specialty, room_number in PROVIDERS:
            user = create_provider_account(actor=admin, school_id=school_id, email=sample_email(first, last),
                                           first_name=first, last_name=last, password=password,
                                           provider_type=designation, specialization=specialty)
            provider = save_provider(actor=admin, provider_id=user.pk, provider_type=designation,
                                     license_number=None, specialization=specialty,
                                     is_active=True, verification_confirmed=True)
            room = save_room(actor=admin, campus="Main Campus", building="Health Services Center",
                             room_number=room_number, is_active=True)
            care_teams.append((provider, room))

        # The new fictional accounts predate their fictional appointment history.
        patient_ids = [patient.pk for patient in patients]
        provider_ids = [provider.pk for provider, _ in care_teams]
        created_at = timezone.now() - timedelta(days=28)
        User.objects.filter(pk__in=patient_ids + provider_ids).update(created_at=created_at)
        Patient.objects.filter(pk__in=patient_ids).update(created_at=created_at)

        appointments, availability = add_bookings(patients, care_teams)
        AuditLog.objects.create(actor_user=admin, action_performed=BATCH_ACTION, target_table="system", target_record_id=0)
        self.stdout.write(self.style.SUCCESS(
            f"Added {len(patients)} patients, {len(care_teams)} providers, {appointments} appointments "
            f"and {availability} available slots."
        ))
