from django.test import TestCase
from django.urls import reverse

from apps.register.models import User


class LoginFeatureTests(TestCase):
    def test_login_page_is_public(self):
        response = self.client.get(reverse("login:login"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_login_and_reach_home(self):
        User.objects.create_user(
            school_id="2026-0001",
            email="student@example.com",
            fname="Campus",
            lname="Student",
            password="test-password-123",
            user_type=User.UserType.PATIENT,
            account_status=User.AccountStatus.ACTIVE,
        )
        response = self.client.post(
            reverse("login:login"),
            {"university_id": "2026-0001", "password": "test-password-123"},
        )
        self.assertRedirects(response, reverse("home:home"))
