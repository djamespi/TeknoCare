from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class LoginFeatureTests(TestCase):
    def test_login_page_is_public(self):
        response = self.client.get(reverse("login:login"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_login_and_reach_home(self):
        User.objects.create_user(username="2026-0001", password="test-password-123")
        response = self.client.post(
            reverse("login:login"),
            {"university_id": "2026-0001", "password": "test-password-123"},
        )
        self.assertRedirects(response, reverse("home:home"))
