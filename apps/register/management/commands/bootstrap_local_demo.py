"""Create fictional local accounts without changing existing accounts."""
from datetime import date
import getpass
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.appointments.models import ClinicRoom
from apps.billing.models import AcademicTerm
from apps.clinical.models import Diagnosis
from apps.patients.models import Affiliation, Patient
from apps.prescriptions.models import Medication
from apps.providers.models import Provider


PATIENTS = (
    ("DEMO-STUDENT", Affiliation.STUDENT),
    ("DEMO-FACULTY", Affiliation.FACULTY),
    ("DEMO-STAFF", Affiliation.STAFF),
)
PROVIDERS = (
    ("DEMO-NURSE", Provider.Type.NURSE),
    ("DEMO-DOCTOR", Provider.Type.PHYSICIAN),
    ("DEMO-DENTIST", Provider.Type.DENTIST),
)


class Command(BaseCommand):
    help = "Create or reuse the fictional DEMO-ADMIN account in the local SQLite database."

    def add_arguments(self, parser):
        parser.add_argument("--noinput", action="store_true", help="Read TEKNOCARE_DEMO_PASSWORD instead of prompting.")
        parser.add_argument("--workflow", action="store_true",
            help="Also prepare fictional Patient and Provider accounts, a room, a term and catalog entries.")

    def handle(self, *args, **options):
        if not settings.TEKNOCARE_LOCAL_DEMO or connection.vendor != "sqlite":
            raise CommandError("Demo setup is restricted to local/test SQLite settings; use --settings=config.settings_local.")
        self.demo_password = None
        try:
            with transaction.atomic():
                message = self.bootstrap(options)
                if options["workflow"]:
                    self.bootstrap_workflow(options)
        except IntegrityError:
            raise CommandError("A conflicting demo entry was found. Existing records were preserved.") from None
        self.stdout.write(message)
        if options["workflow"]:
            self.stdout.write(self.style.SUCCESS("Local workflow accounts, room, term and catalogs are ready."))

    def bootstrap(self, options):
        user_model = get_user_model()
        expected = {
            "email": "admin@teknocare-demo.example.invalid",
            "fname": "Prototype",
            "lname": "Admin",
            "user_type": user_model.UserType.ADMIN,
            "account_status": user_model.AccountStatus.ACTIVE,
        }
        existing = user_model.objects.filter(school_id="DEMO-ADMIN").first()
        if existing:
            if any(getattr(existing, field) != value for field, value in expected.items()):
                raise CommandError("DEMO-ADMIN already has different data. No account was overwritten.")
            return "Reused local DEMO-ADMIN. Its password and existing data are unchanged."

        if user_model.objects.filter(email__iexact=expected["email"]).exists():
            raise CommandError("The reserved demo email is already in use. No account was overwritten.")

        self.create_account(options, school_id="DEMO-ADMIN", **expected)
        return self.style.SUCCESS("Created fictional local DEMO-ADMIN. Sign in with the password you supplied.")

    def create_account(self, options, **fields):
        user = get_user_model()(**fields)
        password = self.get_demo_password(options)
        try:
            validate_password(password, user)
            user.set_password(password)
            user.full_clean()
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from None
        user.save()
        return user

    def get_demo_password(self, options):
        if self.demo_password is not None:
            return self.demo_password
        password = os.environ.get("TEKNOCARE_DEMO_PASSWORD")
        if not password:
            if options["noinput"]:
                raise CommandError("Set TEKNOCARE_DEMO_PASSWORD or omit --noinput to choose a password privately.")
            password = getpass.getpass("Choose a password for the new fictional local accounts: ")
            if password != getpass.getpass("Confirm password: "):
                raise CommandError("Passwords do not match. No account was created.")

        self.demo_password = password
        return password

    def workflow_account(self, options, school_id, label, role):
        user_model = get_user_model()
        fields = {
            "email": f"{school_id.removeprefix('DEMO-').lower()}@teknocare-demo.example.invalid",
            "fname": "Prototype",
            "lname": label,
            "user_type": role,
            "account_status": user_model.AccountStatus.ACTIVE,
        }
        existing = user_model.objects.filter(school_id=school_id).first()
        if existing is None:
            return self.create_account(options, school_id=school_id, **fields)
        if any(getattr(existing, key) != value for key, value in fields.items()):
            raise CommandError(f"{school_id} already has different data. Use a fresh demo database.")
        return existing

    @staticmethod
    def seed_row(model, lookup, expected):
        instance, _ = model.objects.get_or_create(**lookup, defaults=expected)
        if any(getattr(instance, key) != value for key, value in expected.items()):
            raise CommandError(f"A reserved {model._meta.verbose_name} has changed. Use a fresh demo database.")

    def bootstrap_workflow(self, options):
        user_model = get_user_model()
        admin = user_model.objects.get(school_id="DEMO-ADMIN")
        self.seed_row(Patient, {"patient": admin}, {"affiliation": Affiliation.STAFF})
        for school_id, affiliation in PATIENTS:
            user = self.workflow_account(options, school_id, affiliation.label, user_model.UserType.PATIENT)
            self.seed_row(Patient, {"patient": user}, {"affiliation": affiliation})
        for school_id, designation in PROVIDERS:
            user = self.workflow_account(options, school_id, designation.label, user_model.UserType.PROVIDER)
            self.seed_row(Provider, {"provider": user}, {"provider_type": designation, "is_active": True})

        self.seed_row(ClinicRoom, {"campus": "Fictional", "building": "Prototype", "room_number": "DEMO-CLINIC"},
            {"is_active": True})
        today = timezone.localdate()
        year = today.year if today.month >= 8 else today.year - 1
        self.seed_row(AcademicTerm, {"academic_year": f"{year}-{year + 1}", "semester": "Prototype term"}, {
            "start_date": date(year, 8, 1), "end_date": date(year + 1, 7, 31), "is_open_for_charges": True,
        })
        self.seed_row(Diagnosis, {"coding_system": "Prototype", "code": "DEMO-FINDING"},
            {"description": "Fictional demo finding"})
        self.seed_row(Medication, {"medication_code": "DEMO-ITEM"}, {
            "generic_name": "Fictional demo item", "strength": "Training only", "dosage_form": "Prototype", "is_active": True,
        })
