"""Load the Figma Make fixture into the dedicated Django demo database."""
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction

from apps.appointments.models import Appointment, ClinicRoom, Slot
from apps.audit.models import AuditLog
from apps.billing.models import AcademicTerm, StudentCharge
from apps.clinical.models import Diagnosis, MedicalRecord, RecordDiagnosis, Referral, VitalSign
from apps.patients.models import EmergencyContact, Patient, PatientAllergy
from apps.prescriptions.models import Medication, Prescription, PrescriptionItem
from apps.profile.models import Profile
from apps.providers.models import Provider
from apps.register.models import User
from apps.university.models import Department
from apps.user_settings.models import UserSettings


MODELS = [
    Department, User, Patient, Provider, Profile, UserSettings, EmergencyContact,
    PatientAllergy, ClinicRoom, Slot, Appointment, MedicalRecord, VitalSign, Diagnosis,
    RecordDiagnosis, Medication, Prescription, PrescriptionItem, Referral, AcademicTerm,
    StudentCharge, AuditLog,
]
TIMESTAMPS = {"created_at", "start_time", "end_time", "canceled_at", "visited_at", "finalized_at",
              "recorded_at", "issued_at", "referred_at", "posted_at", "voided_at", "logged_at"}
DATES = {"date_of_birth", "start_date", "end_date"}
APPOINTMENT_STATES = {
    "booked": "Scheduled", "checked_in": "Checked-In", "completed": "Completed",
    "canceled": "Canceled", "no_show": "No Show",
}
SAMPLE_TAG = "Figma Make sample import completed"


def rows(data, model):
    for entry in data[model._meta.db_table]:
        yield {
            key: (datetime.fromisoformat(value) if key in TIMESTAMPS else date.fromisoformat(value) if key in DATES else value)
            if value is not None else None
            for key, value in entry.items()
        }


def create_rows(data, model, **overrides):
    for entry in rows(data, model):
        model.objects.create(**{**entry, **overrides})


def import_fixture(data, password):
    create_rows(data, Department)
    for entry in rows(data, User):
        entry.pop("password_hash")
        entry["email"] = f"make-account-{entry['user_id']}@example.invalid"
        entry["user_type"] = entry["user_type"].title()
        entry["account_status"] = "Active" if entry["account_status"] == "active" else "Suspended"
        User.objects.create_user(password=password, **entry)
    for entry in rows(data, Patient):
        entry["affiliation"] = entry["affiliation"].title()
        Patient.objects.create(**entry)
    for entry in rows(data, Provider):
        entry["provider_type"] = entry["provider_type"].title()
        if entry["license_number"]:
            entry["license_number"] = f"DEMO-{entry['provider_id']:04d}"
        Provider.objects.create(**entry)
    create_rows(data, Profile, phone_number=None, home_address=None)
    create_rows(data, UserSettings, email_notifications=False)
    create_rows(data, EmergencyContact, phone_number="+63 000 000 0000")
    for entry in rows(data, PatientAllergy):
        entry["severity"] = entry["severity"].title()
        PatientAllergy.objects.create(**entry)
    create_rows(data, ClinicRoom)
    Slot.objects.bulk_create([Slot(**entry) for entry in rows(data, Slot)], batch_size=300)
    for entry in rows(data, Appointment):
        entry["status"] = APPOINTMENT_STATES[entry["status"]]
        Appointment.objects.create(**entry)
    create_rows(data, Diagnosis)
    create_rows(data, Medication)
    visit_dates = {}
    prescriber_by_record = {
        entry["record_id"]: 2 for entry in data["prescription"] if entry["prescriber_id"] == 3
    }
    for entry in rows(data, MedicalRecord):
        visit_dates[entry["record_id"]] = entry["finalized_at"]
        entry["provider_id"] = prescriber_by_record.get(entry["record_id"], entry["provider_id"])
        MedicalRecord.objects.create(**{**entry, "status": "Draft", "finalized_at": None})
    create_rows(data, VitalSign)
    create_rows(data, RecordDiagnosis)
    for entry in rows(data, Referral):
        # The prototype's Sent and Accepted states are open referrals in Django.
        Referral.objects.create(**{**entry, "status": "Pending"})
    issues = {}
    for entry in rows(data, Prescription):
        issues[entry["prescription_id"]] = entry["issued_at"]
        if entry["prescriber_id"] == 3:
            entry["prescriber_id"] = 2
        Prescription.objects.create(**{**entry, "status": "Draft", "issued_at": None})
    create_rows(data, PrescriptionItem)
    for key, issued_at in issues.items():
        prescription = Prescription.objects.get(pk=key)
        prescription.status, prescription.issued_at = "Issued", issued_at
        prescription.save()
    for key, finalized_at in visit_dates.items():
        if finalized_at:
            record = MedicalRecord.objects.get(pk=key)
            record.status, record.finalized_at = "Finalized", finalized_at
            record.save()
    create_rows(data, AcademicTerm)
    for entry in rows(data, StudentCharge):
        posted_at = entry["posted_at"]
        charge = StudentCharge.objects.create(**{
            **entry, "description": "Sample clinic visit charge", "status": "Pending",
            "posted_at": None, "billing_reference": None,
        })
        if posted_at:
            charge.status = "Posted"
            charge.posted_at = posted_at
            charge.billing_reference = f"DEMO-POST-{charge.charge_code}"
            charge.save()
    for entry in rows(data, AuditLog):
        entry["action_performed"] = "Sample: " + entry["action_performed"]
        AuditLog.objects.create(**entry)
    with connection.cursor() as cursor:
        for statement in connection.ops.sequence_reset_sql(no_style(), MODELS):
            cursor.execute(statement)
    AuditLog.objects.create(action_performed=SAMPLE_TAG, target_table="system", target_record_id=0)


class Command(BaseCommand):
    help = "Import the Make sample records into the dedicated demo database."

    def add_arguments(self, parser):
        parser.add_argument("fixture", type=Path)
        parser.add_argument("--credentials-file", type=Path, required=True,
                            help="Private file containing the sample account password.")

    def handle(self, fixture, credentials_file, **options):
        if not getattr(settings, "TEKNOCARE_MAKE_DEMO", False) or connection.vendor != "postgresql":
            raise CommandError("Use config.settings_make_demo for this import.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            if cursor.fetchone()[0] != "teknocare_make_demo":
                raise CommandError("The connection is not the dedicated demo database.")
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", (790441358,))
            if AuditLog.objects.filter(action_performed=SAMPLE_TAG).exists():
                self.stdout.write("The Make sample has already been imported.")
                return
            if any(model.objects.exists() for model in MODELS):
                raise CommandError("The demo database contains existing clinic rows. Review it before importing.")
            data = json.loads(fixture.read_text(encoding="utf-8"), parse_float=Decimal)
            password = credentials_file.read_text(encoding="utf-8").strip()
            if len(password) < 16:
                raise CommandError("Choose a demo password of at least 16 characters.")
            import_fixture(data, password)
        self.stdout.write(self.style.SUCCESS("Imported the Figma Make sample into teknocare_make_demo."))
