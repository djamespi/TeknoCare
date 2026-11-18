from django.test import Client, TestCase
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

    def test_password_change_invalidates_existing_session(self):
        user = User.objects.create_user(school_id="SESSION-TEST", email="session@example.invalid", password="old-password")
        self.client.force_login(user)
        user.set_password("new-password")
        user.save(update_fields=["password_hash"])
        url = reverse("home:home")
        self.assertRedirects(self.client.get(url), f"{reverse('login:login')}?next={url}")

    def test_active_admin_can_open_django_admin(self):
        admin = User.objects.create_superuser(school_id="ADMIN-TEST", email="admin@example.invalid", password="test-password")
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_logout_requires_post_and_valid_csrf_token(self):
        user = User.objects.create_superuser(school_id="LOGOUT-TEST", email="logout@example.invalid", password="test-password")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        self.assertEqual(client.get(reverse("logout")).status_code, 405)
        self.assertEqual(client.post(reverse("logout")).status_code, 403)
        self.assertEqual(client.get(reverse("home:home")).status_code, 200)
        token = client.cookies["csrftoken"].value
        response = client.post(reverse("logout"), {"csrfmiddlewaretoken": token})
        self.assertRedirects(response, reverse("login:login"))
        self.assertNotIn("_auth_user_id", client.session)
