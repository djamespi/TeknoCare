from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.common.test_data import clinic_data
from apps.patients.models import Patient
from apps.providers.models import Provider
from apps.register.models import User
from apps.register.services import change_password, reset_account_password, set_account_status
from .backends import ClinicBackend


class AccountSecurityTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()
        self.user = self.patient.patient
        self.home = reverse("home:home")
        self.login = reverse("login:login")
        self.change = reverse("login:password_change")
        self.reset = reverse("login:admin_password_reset")
        self.new_password = "Replacement-secret-6529!"

    def password_payload(self, **overrides):
        values = dict(old_password="test-password", new_password1=self.new_password, new_password2=self.new_password)
        values.update(overrides)
        return values

    def reset_payload(self, **overrides):
        values = dict(university_id=self.user.school_id, admin_password="test-password",
            new_password1=self.new_password, new_password2=self.new_password)
        values.update(overrides)
        return values

    def test_login_preserves_trimmed_id_and_uses_generic_denial(self):
        response = self.client.post(self.login, {"university_id": f" {self.user.school_id} ", "password": "test-password"})
        self.assertRedirects(response, self.home)
        self.assertEqual(AuditLog.objects.get().action_performed, "Account signed in")
        self.client.logout()
        for username, password in ((self.user.school_id.lower(), "test-password"), (self.user.school_id, "incorrect"), ("MISSING", "test-password")):
            response = self.client.post(self.login, {"university_id": username, "password": password})
            self.assertContains(response, "Invalid University ID or password")
            self.assertNotIn("_auth_user_id", self.client.session)

    def test_redirects_only_allow_local_targets(self):
        for target in ("https://attacker.invalid/", "//attacker.invalid/", "javascript:alert(1)", "/login/", "/logout/"):
            with self.subTest(target=target):
                self.client.logout()
                response = self.client.post(self.login, {"university_id": self.user.school_id, "password": "test-password", "next": target})
                self.assertRedirects(response, self.home)
        self.client.logout()
        profile = reverse("profile:profile")
        response = self.client.post(f"{self.login}?next={profile}", {"university_id": self.user.school_id, "password": "test-password"})
        self.assertRedirects(response, profile)

    def test_missing_required_profiles_deny_login_and_existing_sessions_cleanly(self):
        for role in ("Patient", "Provider"):
            user = User.objects.create_user(role, f"{role}@example.invalid", "test-password", user_type=role)
            self.assertIsNone(authenticate(username=user.school_id, password="test-password"))
            self.client.force_login(user)
            self.assertRedirects(self.client.get(self.home), f"{self.login}?next={self.home}")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.home).status_code, 200)
        other = User.objects.create_user("REMOVE-PROFILE", "remove@example.invalid", "test-password")
        profile = Patient.objects.create(patient=other, affiliation="Staff")
        self.client.force_login(other)
        profile.delete()
        self.assertRedirects(self.client.get(self.home), f"{self.login}?next={self.home}")

    def test_inactive_provider_can_use_account_without_clinical_activation(self):
        Provider.objects.filter(pk=self.provider.pk).update(is_active=False)
        self.assertEqual(authenticate(username=self.provider.provider.school_id, password="test-password").pk, self.provider.pk)

    def test_async_backend_uses_the_same_custom_user_and_access_rules(self):
        backend = ClinicBackend()
        self.assertEqual(async_to_sync(backend.aauthenticate)(None, username=self.user.school_id, password="test-password").pk, self.user.pk)
        self.assertEqual(async_to_sync(backend.aget_user)(self.user.pk).pk, self.user.pk)
        self.assertTrue(async_to_sync(backend.ahas_perm)(self.admin, "register.view_user"))
        self.assertFalse(async_to_sync(backend.ahas_perm)(self.admin, "register.change_user"))
        User.objects.filter(pk=self.user.pk).update(account_status="Suspended")
        self.assertIsNone(async_to_sync(backend.aget_user)(self.user.pk))

    def test_suspension_denies_new_and_existing_sessions_and_reactivation_does_not_revive(self):
        self.client.force_login(self.user)
        other = Client()
        other.force_login(self.user)
        admin_client = Client()
        admin_client.force_login(self.admin)
        set_account_status(actor=self.admin, user_id=self.user.pk, status="Suspended")
        self.assertIsNone(authenticate(username=self.user.school_id, password="test-password"))
        self.assertRedirects(self.client.get(self.home), f"{self.login}?next={self.home}")
        self.assertEqual(admin_client.get(self.home).status_code, 200)
        set_account_status(actor=self.admin, user_id=self.user.pk, status="Active")
        self.assertRedirects(other.get(self.home), f"{self.login}?next={self.home}")
        self.assertIsNotNone(authenticate(username=self.user.school_id, password="test-password"))

    def test_password_change_keeps_current_session_and_invalidates_others(self):
        self.client.force_login(self.user)
        old_key = self.client.session.session_key
        other = Client()
        other.force_login(self.user)
        response = self.client.post(self.change, self.password_payload(user_id=self.admin.pk))
        self.assertRedirects(response, self.change)
        self.assertNotEqual(self.client.session.session_key, old_key)
        self.assertEqual(self.client.get(self.home).status_code, 200)
        self.assertRedirects(other.get(self.home), f"{self.login}?next={self.home}")
        self.user.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertTrue(self.admin.check_password("test-password"))
        self.assertIsNone(authenticate(username=self.user.school_id, password="test-password"))
        event = AuditLog.objects.get()
        self.assertEqual((event.actor_user_id, event.target_record_id), (self.user.pk, self.user.pk))
        self.assertNotIn(self.new_password, event.action_performed)

    def test_password_errors_leave_hash_and_sessions_unchanged(self):
        self.client.force_login(self.user)
        original_hash = self.user.password_hash
        for override, field in ((dict(old_password="wrong"), "old_password"), (dict(new_password2="mismatch"), "new_password2"),
            (dict(new_password1="12345678", new_password2="12345678"), "new_password1")):
            with self.subTest(field=field):
                response = self.client.post(self.change, self.password_payload(**override))
                self.assertIn(field, response.context["form"].errors)
                self.user.refresh_from_db()
                self.assertEqual(self.user.password_hash, original_hash)
                self.assertEqual(self.client.get(self.home).status_code, 200)
        self.assertFalse(AuditLog.objects.exists())

    def test_audit_failure_rolls_back_password_change(self):
        original_hash = self.user.password_hash
        with patch("apps.register.services._audit", side_effect=ValidationError("Audit unavailable")):
            with self.assertRaises(ValidationError):
                change_password(actor=self.user, old_password="test-password", new_password=self.new_password)
        self.user.refresh_from_db()
        self.assertEqual(self.user.password_hash, original_hash)

    def test_reset_is_admin_only_and_rechecks_admin_password(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.reset).status_code, 403)
        self.assertEqual(self.client.post(self.reset, self.reset_payload()).status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.post(self.reset, self.reset_payload(admin_password="incorrect"))
        self.assertIn("admin_password", response.context["form"].errors)
        response = self.client.post(self.reset, self.reset_payload(university_id="MISSING"))
        self.assertIn("university_id", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("test-password"))

    def test_admin_reset_revokes_other_sessions_without_changing_role_or_status(self):
        other = Client()
        other.force_login(self.user)
        self.client.force_login(self.admin)
        response = self.client.post(self.reset, self.reset_payload())
        self.assertRedirects(response, self.reset)
        self.assertRedirects(other.get(self.home), f"{self.login}?next={self.home}")
        self.user.refresh_from_db()
        self.assertEqual((self.user.user_type, self.user.account_status), ("Patient", "Active"))
        self.assertTrue(self.user.check_password(self.new_password))
        self.assertEqual(AuditLog.objects.get().actor_user_id, self.admin.pk)
        User.objects.filter(pk=self.user.pk).update(account_status="Suspended")
        reset_account_password(actor=self.admin, school_id=self.user.school_id, admin_password="test-password", new_password="Another-secret-5732!")
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_status, "Suspended")
        self.assertIsNone(authenticate(username=self.user.school_id, password="Another-secret-5732!"))

    def test_reset_cannot_target_self_or_another_admin_and_validates_new_password(self):
        other_admin = User.objects.create_superuser("OTHER-ADMIN", "other-admin@example.invalid", "test-password")
        self.client.force_login(self.admin)
        for target in (self.admin, other_admin):
            self.assertEqual(self.client.post(self.reset, self.reset_payload(university_id=target.school_id)).status_code, 403)
        response = self.client.post(self.reset, self.reset_payload(new_password1="12345678", new_password2="12345678"))
        self.assertIn("new_password1", response.context["form"].errors)

    def test_mutation_forms_require_csrf_and_reject_unexpected_methods(self):
        client = Client(enforce_csrf_checks=True)
        for url in (self.login, reverse("register:register")):
            self.assertEqual(client.post(url, {}).status_code, 403)
        client.force_login(self.admin)
        for url in (self.change, self.reset):
            self.assertEqual(client.get(url).status_code, 200)
            self.assertEqual(client.post(url, {}).status_code, 403)
            self.assertEqual(client.put(url, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value).status_code, 405)
        for url in (self.login, reverse("register:register")):
            self.assertEqual(self.client.put(url).status_code, 405)

    def test_password_navigation_is_role_scoped(self):
        self.client.force_login(self.user)
        response = self.client.get(self.home)
        self.assertContains(response, f'href="{self.change}"')
        self.assertNotContains(response, f'href="{self.reset}"')
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.home), f'href="{self.reset}"')

    def test_django_admin_is_read_only_and_never_displays_password_hash(self):
        self.client.force_login(self.admin)
        self.assertFalse(self.admin.is_superuser)
        self.assertFalse(self.admin.has_perm("register.change_user"))
        self.assertEqual(self.client.get(reverse("admin:register_user_changelist")).status_code, 200)
        detail = reverse("admin:register_user_change", args=[self.user.pk])
        response = self.client.get(detail)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.user.password_hash)
        self.assertNotContains(response, "password_hash")
        self.assertEqual(self.client.post(detail, {"user_type": "Admin"}).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:register_user_add")).status_code, 403)
        self.assertEqual(self.client.post(reverse("admin:register_user_delete", args=[self.user.pk]), {"post": "yes"}).status_code, 403)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)
