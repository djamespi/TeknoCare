from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegisterFeatureTests(TestCase):
    def test_student_can_register_with_university_id(self):
        response = self.client.post(
            reverse("register:register"),
            {
                "university_id": "2026-0002",
                "first_name": "Alex",
                "last_name": "Student",
                "email": "alex@example.com",
                "age": 20,
                "home_address": "12 Campus Road",
                "password1": "test-password-123",
                "password2": "test-password-123",
            },
        )

        self.assertRedirects(response, reverse("login:login"))
        user = User.objects.get(username="2026-0002")
        self.assertEqual(user.first_name, "Alex")
        self.assertEqual(user.last_name, "Student")
        self.assertEqual(user.email, "alex@example.com")
        self.assertEqual(user.clinic_profile.age, 20)
        self.assertEqual(user.clinic_profile.home_address, "12 Campus Road")

    def test_duplicate_university_id_is_rejected(self):
        User.objects.create_user(username="2026-0002", password="test-password-123")

        response = self.client.post(
            reverse("register:register"),
            {
                "university_id": "2026-0002",
                "first_name": "Alex",
                "last_name": "Student",
                "email": "alex@example.com",
                "age": 20,
                "home_address": "12 Campus Road",
                "password1": "test-password-123",
                "password2": "test-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")