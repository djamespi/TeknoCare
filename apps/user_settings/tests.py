from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class SettingsFeatureTests(TestCase):
    def test_authenticated_user_can_save_settings(self):
        user = User.objects.create_user(username="student", password="test-password-123")
        self.client.force_login(user)
        response = self.client.post(reverse("user_settings:settings"), {"dark_mode": "on"})
        self.assertRedirects(response, reverse("user_settings:settings"))
        self.assertTrue(user.clinic_settings.dark_mode)
