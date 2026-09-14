from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class ProfileFeatureTests(TestCase):
    def test_authenticated_user_can_save_profile(self):
        user = User.objects.create_user(username="student", password="test-password-123")
        self.client.force_login(user)
        response = self.client.post(reverse("profile:profile"), {"full_name": "Campus Student", "bio": "Ready for care."})
        self.assertRedirects(response, reverse("profile:profile"))
        self.assertEqual(user.clinic_profile.full_name, "Campus Student")
