from django.test import Client, TestCase
from django.urls import reverse

from apps.common.test_data import clinic_data
from apps.patients.models import Patient
from apps.university.models import Department
from .models import User


class PersonnelManagementTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()
        self.department = Department.objects.create(code="FIC", name="Fictional Department")
        self.client.force_login(self.admin)

    def payload(self, **overrides):
        values = dict(school_id=" 001-Staff ", first_name="Fictional", last_name="Employee", email="Employee@Example.INVALID",
            password1="Private-test-secret-5829!", password2="Private-test-secret-5829!", affiliation="Staff", department=self.department.pk)
        values.update(overrides)
        return values

    def test_personnel_intake_creates_patient_without_role_or_status_injection(self):
        response = self.client.post(reverse("accounts:personnel_create"), self.payload(user_type="Admin", account_status="Suspended"), follow=True)
        self.assertContains(response, "Personnel account created")
        user = User.objects.get(school_id="001-Staff")
        self.assertEqual((user.user_type, user.account_status, user.email), ("Patient", "Active", "employee@example.invalid"))
        self.assertEqual((user.patient_profile.affiliation, user.patient_profile.department_id), ("Staff", self.department.pk))
        self.assertFalse(user.created_charges.exists())

    def test_invalid_affiliation_weak_password_and_inactive_department_are_rejected(self):
        for override in (dict(affiliation="Student"), dict(password1="12345678", password2="12345678")):
            response = self.client.post(reverse("accounts:personnel_create"), self.payload(**override))
            self.assertTrue(response.context["form"].errors)
        self.department.is_active = False
        self.department.save()
        response = self.client.post(reverse("accounts:personnel_create"), self.payload())
        self.assertIn("department", response.context["form"].errors)
        self.assertFalse(User.objects.filter(school_id="001-Staff").exists())

    def test_faculty_can_be_provisioned_without_guessing_department(self):
        response = self.client.post(reverse("accounts:personnel_create"), self.payload(affiliation="Faculty", department=""))
        self.assertRedirects(response, reverse("accounts:personnel_list"))
        patient = Patient.objects.get(patient__school_id="001-Staff")
        self.assertEqual(patient.affiliation, "Faculty")
        self.assertIsNone(patient.department_id)

    def test_suspension_revokes_session_without_changing_role_and_cannot_target_admin(self):
        other = Client()
        other.force_login(self.provider.provider)
        response = self.client.post(reverse("accounts:status", args=[self.provider.pk]), {"account_status": "Suspended", "confirm": "on"})
        self.assertRedirects(response, reverse("university:management"))
        self.assertEqual(other.get(reverse("home:home")).status_code, 302)
        user = User.objects.get(pk=self.provider.pk)
        self.assertEqual((user.user_type, user.account_status), ("Provider", "Suspended"))
        self.assertEqual(self.record.provider_id, user.pk)
        self.assertEqual(self.client.post(reverse("accounts:status", args=[self.admin.pk]), {"account_status": "Suspended", "confirm": "on"}).status_code, 403)

    def test_access_change_requires_confirmation(self):
        response = self.client.post(reverse("accounts:status", args=[self.patient.pk]), {"account_status": "Suspended"})
        self.assertIn("confirm", response.context["form"].errors)
        self.patient.patient.refresh_from_db()
        self.assertTrue(self.patient.patient.is_active)
