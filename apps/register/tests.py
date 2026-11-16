from django.test import TestCase
from django.urls import reverse

from .models import User
from apps.patients.models import Patient


class RegisterFeatureTests(TestCase):
    def test_student_can_register_with_university_id(self):
        response = self.client.post(
            reverse("register:register"),
            {
                "university_id": "2026-0002",
                "first_name": "Alex",
                "last_name": "Student",
                "email": "alex@example.com",
                "emergency_contact": "09171234567",
                "emergency_contact_name": "Jamie Student",
                "emergency_contact_relationship": "Parent",
                "medical_history_summary": "No known allergies",
                "password1": "test-password-123",
                "password2": "test-password-123",
            },
        )

        self.assertRedirects(response, reverse("login:login"))
        user = User.objects.get(school_id="2026-0002")
        self.assertEqual(user.fname, "Alex")
        self.assertEqual(user.lname, "Student")
        self.assertEqual(user.email, "alex@example.com")
        self.assertEqual(user.user_type, User.UserType.PATIENT)
        self.assertEqual(user.patient_profile.emergency_contacts.get(is_primary=True).phone_number, "09171234567")
        self.assertIsInstance(user.patient_profile, Patient)

    def test_duplicate_university_id_is_rejected(self):
        User.objects.create_user(
            school_id="2026-0002",
            email="existing@example.com",
            fname="Existing",
            lname="Student",
            password="test-password-123",
            user_type=User.UserType.PATIENT,
            account_status=User.AccountStatus.ACTIVE,
        )

        response = self.client.post(
            reverse("register:register"),
            {
                "university_id": "2026-0002",
                "first_name": "Alex",
                "last_name": "Student",
                "email": "alex@example.com",
                "emergency_contact": "09171234567",
                "emergency_contact_name": "Jamie Student",
                "emergency_contact_relationship": "Parent",
                "medical_history_summary": "No known allergies",
                "password1": "test-password-123",
                "password2": "test-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")