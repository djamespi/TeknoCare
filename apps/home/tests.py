from django.test import TestCase
from django.urls import reverse

from apps.profile.models import Profile
from apps.register.models import User
from apps.user_settings.models import UserSettings


class AccountPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            school_id="2026-0010",
            email="account@example.com",
            fname="Alex",
            lname="Student",
            password="test-password-123",
            user_type=User.UserType.PATIENT,
            account_status=User.AccountStatus.ACTIVE,
        )
        cls.other_user = User.objects.create_user(
            school_id="2026-0011",
            email="other@example.com",
            fname="Other",
            lname="Student",
            password="test-password-123",
            user_type=User.UserType.PATIENT,
            account_status=User.AccountStatus.ACTIVE,
        )

    def test_account_pages_require_login(self):
        for name in ("home:home", "home:dashboard", "profile:profile", "user_settings:settings"):
            with self.subTest(page=name):
                url = reverse(name)
                self.assertRedirects(self.client.get(url), f"{reverse('login:login')}?next={url}")

    def test_account_pages_render_with_navigation(self):
        self.client.force_login(self.user)
        for name, template in (
            ("home:home", "home/home.html"),
            ("home:dashboard", "home/home.html"),
            ("profile:profile", "profile/profile.html"),
            ("user_settings:settings", "user_settings/settings.html"),
        ):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                for link in ("home:home", "profile:profile", "user_settings:settings"):
                    self.assertContains(response, f'href="{reverse(link)}"')

    def test_dashboard_shows_account_cards(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("home:home"))
        self.assertContains(response, "Good to see you, Alex.")
        self.assertContains(response, "Your profile")
        self.assertContains(response, "YOUR PREFERENCES")

    def test_profile_changes_only_current_user(self):
        other_profile = Profile.objects.create(user=self.other_user, full_name="Other Student")
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile:profile"), {
            "full_name": "Alex Student", "age": "21",
            "home_address": "Cebu City", "bio": "Hello clinic",
        })
        self.assertRedirects(response, reverse("profile:profile"))
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.full_name, "Alex Student")
        self.assertEqual(profile.age, 21)
        self.assertEqual(profile.home_address, "Cebu City")
        self.assertEqual(profile.bio, "Hello clinic")
        other_profile.refresh_from_db()
        self.assertEqual(other_profile.full_name, "Other Student")

    def test_invalid_profile_is_not_saved(self):
        profile = Profile.objects.create(user=self.user, age=21)
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile:profile"), {"age": "-1"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        profile.refresh_from_db()
        self.assertEqual(profile.age, 21)

    def test_settings_changes_only_current_user(self):
        other_settings = UserSettings.objects.create(user=self.other_user)
        self.client.force_login(self.user)
        response = self.client.post(reverse("user_settings:settings"), {"dark_mode": "on"})
        self.assertRedirects(response, reverse("user_settings:settings"))
        settings = UserSettings.objects.get(user=self.user)
        self.assertTrue(settings.dark_mode)
        self.assertFalse(settings.email_notifications)
        other_settings.refresh_from_db()
        self.assertFalse(other_settings.dark_mode)
        self.assertTrue(other_settings.email_notifications)

    def test_settings_can_save_both_checkboxes_unchecked(self):
        UserSettings.objects.create(user=self.user, dark_mode=True, email_notifications=True)
        self.client.force_login(self.user)
        response = self.client.post(reverse("user_settings:settings"), {})
        self.assertRedirects(response, reverse("user_settings:settings"))
        settings = UserSettings.objects.get(user=self.user)
        self.assertFalse(settings.dark_mode)
        self.assertFalse(settings.email_notifications)

    def test_profile_and_settings_labels_support_custom_user(self):
        self.assertEqual(str(Profile(user=self.user)), "Alex Student")
        self.assertEqual(str(UserSettings(user=self.user)), "Settings for Alex Student")
