from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.patients.models import EmergencyContact, Patient
from apps.providers.models import Provider
from .models import User
from .services import add_patient_profile, create_personnel_account, create_provider_account, register_student


class ProvisioningTests(TestCase):
    def student_values(self, **overrides):
        values = dict(school_id=" 001-AbC ", email=" Student@Example.INVALID ", first_name="Casey", last_name="Learner",
            password="Fictional-secret-4729!", contact_name="Taylor Learner", contact_relationship="Parent", contact_phone="09000000001")
        values.update(overrides)
        return values

    def account_values(self, **overrides):
        values = dict(school_id="PERSON-001", email="person@example.invalid", first_name="Fictional", last_name="Person", password="Fictional-secret-4729!")
        values.update(overrides)
        return values

    def test_registration_normalizes_identity_preserves_id_case_and_creates_complete_patient(self):
        user = register_student(**self.student_values())
        self.assertEqual(user.school_id, "001-AbC")
        self.assertEqual(user.email, "student@example.invalid")
        self.assertTrue(user.check_password("Fictional-secret-4729!"))
        self.assertNotEqual(user.password_hash, "Fictional-secret-4729!")
        self.assertEqual(user.patient_profile.affiliation, "Student")
        self.assertEqual(user.patient_profile.emergency_contacts.filter(is_primary=True).count(), 1)
        self.assertEqual(AuditLog.objects.get().target_record_id, user.pk)

    def test_password_validators_apply_at_service_boundary(self):
        for password in ("short", "123456789", "password", "Casey1234"):
            with self.subTest(password=password), self.assertRaises(ValidationError):
                register_student(**self.student_values(password=password))
        self.assertFalse(User.objects.exists())

    def test_subtype_failure_rolls_back_account_and_audit(self):
        with patch("apps.register.services.EmergencyContact.objects.create", side_effect=ValidationError("Invalid contact")):
            with self.assertRaises(ValidationError):
                register_student(**self.student_values())
        self.assertEqual((User.objects.count(), Patient.objects.count(), EmergencyContact.objects.count(), AuditLog.objects.count()), (0, 0, 0, 0))

    def test_admin_provisions_personnel_and_inactive_provider_without_invented_license(self):
        admin = User.objects.create_superuser("ADMIN", "admin@example.invalid", "Test-admin-482!")
        for affiliation in ("Faculty", "Staff"):
            user = create_personnel_account(actor=admin, affiliation=affiliation,
                **self.account_values(school_id=affiliation, email=f"{affiliation}@example.invalid"))
            self.assertEqual(user.user_type, "Patient")
            self.assertEqual(user.patient_profile.affiliation, affiliation)
        provider_user = create_provider_account(actor=admin, **self.account_values(), license_number="  ")
        self.assertEqual(provider_user.user_type, "Provider")
        self.assertEqual(provider_user.provider_profile.provider_type, Provider.Type.UNVERIFIED)
        self.assertIsNone(provider_user.provider_profile.license_number)
        self.assertFalse(provider_user.provider_profile.is_active)
        for user in (admin, provider_user):
            patient = add_patient_profile(actor=admin, user_id=user.pk, affiliation="Staff")
            self.assertEqual(patient.pk, user.pk)
        with self.assertRaises(ValidationError):
            add_patient_profile(actor=admin, user_id=provider_user.pk, affiliation="Faculty")

    def test_non_admin_and_stale_admin_cannot_provision(self):
        student = register_student(**self.student_values())
        admin = User.objects.create_superuser("ADMIN", "admin@example.invalid", "Test-admin-482!")
        User.objects.filter(pk=admin.pk).update(account_status="Suspended")
        for actor in (student, admin, None):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                create_provider_account(actor=actor, **self.account_values())
        self.assertFalse(Provider.objects.exists())

    def test_normalized_duplicates_are_rejected_even_by_bulk_writes(self):
        register_student(**self.student_values())
        for values in (dict(school_id=" 001-AbC ", email="other@example.invalid"),
            dict(school_id="OTHER", email=" STUDENT@EXAMPLE.INVALID ")):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                User.objects.bulk_create([User(**values, fname="Other", lname="Person", password_hash="!", user_type="Patient", account_status="Active")])

    def registration_payload(self, **overrides):
        values = dict(university_id="001-AbC", email="Student@Example.INVALID", first_name="Casey", last_name="Learner",
            password1="Fictional-secret-4729!", password2="Fictional-secret-4729!", emergency_contact_name="Taylor",
            emergency_contact_relationship="Parent", emergency_contact="09000000001", medical_history_summary="Fictional history")
        values.update(overrides)
        return values

    def test_public_registration_ignores_role_and_affiliation_injection(self):
        response = self.client.post(reverse("register:register"), self.registration_payload(user_type="Admin", affiliation="Staff", account_status="Suspended"))
        self.assertRedirects(response, reverse("login:login"))
        user = User.objects.get(school_id="001-AbC")
        self.assertEqual((user.user_type, user.account_status, user.patient_profile.affiliation), ("Patient", "Active", "Student"))

    def test_public_registration_reports_weak_password_and_normalized_email_duplicate(self):
        response = self.client.post(reverse("register:register"), self.registration_payload(password1="12345678", password2="12345678"))
        self.assertIn("password1", response.context["form"].errors)
        self.assertFalse(User.objects.exists())
        register_student(**self.student_values())
        response = self.client.post(reverse("register:register"), self.registration_payload(university_id="OTHER"))
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_registration_race_returns_form_error_and_rolls_back_partial_account(self):
        with patch("apps.register.services.EmergencyContact.objects.create", side_effect=IntegrityError("simulated race")):
            response = self.client.post(reverse("register:register"), self.registration_payload())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "just registered")
        self.assertFalse(User.objects.exists())
        self.assertFalse(Patient.objects.exists())
