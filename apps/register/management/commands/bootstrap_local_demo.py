"""Create one fictional local administrator without changing existing accounts."""
import getpass
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, connection, transaction


class Command(BaseCommand):
    help = "Create or reuse the fictional DEMO-ADMIN account in the local SQLite database."

    def add_arguments(self, parser):
        parser.add_argument("--noinput", action="store_true", help="Read TEKNOCARE_DEMO_PASSWORD instead of prompting.")

    def handle(self, *args, **options):
        if not settings.TEKNOCARE_LOCAL_DEMO or connection.vendor != "sqlite":
            raise CommandError("Demo setup is restricted to local/test SQLite settings; use --settings=config.settings_local.")
        try:
            with transaction.atomic():
                self.bootstrap(options)
        except IntegrityError:
            raise CommandError("A conflicting demo account was created. No existing account was overwritten.") from None

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
            self.stdout.write("Reused local DEMO-ADMIN. Its password and existing data are unchanged.")
            return

        if user_model.objects.filter(email__iexact=expected["email"]).exists():
            raise CommandError("The reserved demo email is already in use. No account was overwritten.")

        password = os.environ.get("TEKNOCARE_DEMO_PASSWORD")
        if not password:
            if options["noinput"]:
                raise CommandError("Set TEKNOCARE_DEMO_PASSWORD or omit --noinput to choose a password privately.")
            password = getpass.getpass("Choose a password for the fictional local DEMO-ADMIN: ")
            if password != getpass.getpass("Confirm password: "):
                raise CommandError("Passwords do not match. No account was created.")

        user = user_model(school_id="DEMO-ADMIN", **expected)
        try:
            validate_password(password, user)
            user.set_password(password)
            user.full_clean()
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from None
        user.save()
        self.stdout.write(self.style.SUCCESS("Created fictional local DEMO-ADMIN. Sign in with the password you supplied."))
