from io import StringIO
import os
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import authenticate
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings

from .models import User


class DemoDatabaseBoundaryTests(SimpleTestCase):
    @override_settings(TEKNOCARE_LOCAL_DEMO=False)
    def test_demo_setup_refuses_non_demo_configuration_without_database_access(self):
        with self.assertRaisesMessage(CommandError, "restricted to local/test SQLite"):
            call_command("bootstrap_local_demo", noinput=True, stdout=StringIO())


@skipUnless(connection.vendor == "sqlite", "Demo creation is intentionally restricted to SQLite")
@override_settings(TEKNOCARE_LOCAL_DEMO=True)
class LocalDemoSetupTests(TestCase):
    def bootstrap(self, password="Local-demo-test-password-4792!"):
        output = StringIO()
        with patch.dict(os.environ, {"TEKNOCARE_DEMO_PASSWORD": password}):
            call_command("bootstrap_local_demo", noinput=True, stdout=output)
        return output.getvalue()

    def test_creates_authenticatable_admin_with_hashed_password(self):
        self.bootstrap()
        user = User.objects.get(school_id="DEMO-ADMIN")
        self.assertEqual(user.user_type, User.UserType.ADMIN)
        self.assertTrue(user.is_active)
        self.assertNotEqual(user.password_hash, "Local-demo-test-password-4792!")
        self.assertEqual(authenticate(username="DEMO-ADMIN", password="Local-demo-test-password-4792!"), user)
        self.assertFalse(User.objects.filter(school_id__startswith="JOIN-DEMO-").exists())

    def test_repeat_setup_does_not_reset_password_or_duplicate_account(self):
        self.bootstrap()
        original_hash = User.objects.get(school_id="DEMO-ADMIN").password_hash
        self.assertIn("Reused", self.bootstrap("A-different-demo-password-5921!"))
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().password_hash, original_hash)

    def test_conflicting_reserved_id_is_not_overwritten(self):
        existing = User.objects.create_user("DEMO-ADMIN", "someone@example.invalid", "Existing-test-password-19!")
        with self.assertRaisesMessage(CommandError, "different data"):
            self.bootstrap()
        existing.refresh_from_db()
        self.assertEqual(existing.email, "someone@example.invalid")
        self.assertTrue(existing.check_password("Existing-test-password-19!"))

    def test_conflicting_reserved_email_is_not_overwritten(self):
        User.objects.create_user("OTHER-DEMO", "admin@teknocare-demo.example.invalid", "Existing-test-password-19!")
        with self.assertRaisesMessage(CommandError, "email is already in use"):
            self.bootstrap()
        self.assertFalse(User.objects.filter(school_id="DEMO-ADMIN").exists())

    def test_weak_or_missing_password_creates_no_account(self):
        for password in ("12345678", ""):
            with self.subTest(password=password), self.assertRaises(CommandError):
                self.bootstrap(password)
        self.assertEqual(User.objects.count(), 0)

    def test_password_change_command_works_with_custom_user(self):
        self.bootstrap()
        with patch("django.contrib.auth.management.commands.changepassword.Command._get_pass", return_value="Changed-demo-password-5821!"):
            call_command("changepassword", "DEMO-ADMIN", stdout=StringIO())
        user = User.objects.get(school_id="DEMO-ADMIN")
        self.assertTrue(user.check_password("Changed-demo-password-5821!"))
        self.assertFalse(user.check_password("Local-demo-test-password-4792!"))
