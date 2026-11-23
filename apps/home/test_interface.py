from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory, TestCase
from django.urls import resolve, reverse

from apps.common.test_data import clinic_data
from apps.common.test_interface_components import PageMarkup
from apps.patients.models import Patient
from apps.profile.models import Profile
from apps.providers.models import Provider
from apps.user_settings.context_processors import appearance
from apps.user_settings.models import UserSettings


class SharedInterfaceTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()
        self.user = self.patient.patient
        self.pages = ("home:home", "home:dashboard", "profile:profile", "user_settings:settings", "login:password_change")

    def test_existing_pages_use_shared_layout_and_accessible_landmarks(self):
        for name in ("login:login", "register:register"):
            response = self.client.get(reverse(name))
            self.assertTemplateUsed(response, "base.html")
            self.assertContains(response, 'data-theme="light"')
            self.assertNotContains(response, 'aria-label="Main navigation"')
        self.client.force_login(self.admin)
        for name in (*self.pages, "login:admin_password_reset"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "base.html")
                markup = PageMarkup(response.content.decode())
                self.assertEqual(sum(tag == "h1" for tag, attrs in markup.elements), 1)
                self.assertEqual(sum(tag == "main" for tag, attrs in markup.elements), 1)
                element_ids = {attrs["id"] for tag, attrs in markup.elements if "id" in attrs}
                for tag, attrs in markup.elements:
                    if tag == "label" and "for" in attrs:
                        self.assertIn(attrs["for"], element_ids)
                    for reference in attrs.get("aria-describedby", "").split():
                        self.assertIn(reference, element_ids)
                self.assertContains(response, 'href="#main-content"')
                self.assertContains(response, 'aria-label="Main navigation"')
                self.assertContains(response, '/static/css/includes/site.css')
                self.assertContains(response, '/static/js/includes/forms.js')

    def test_default_theme_does_not_create_settings_or_profile_on_get(self):
        self.client.force_login(self.user)
        for name in self.pages:
            self.assertContains(self.client.get(reverse(name)), 'data-theme="light"')
        self.assertFalse(UserSettings.objects.filter(user=self.user).exists())
        self.assertFalse(Profile.objects.filter(user=self.user).exists())
        request = RequestFactory().get("/login/")
        request.user = AnonymousUser()
        with self.assertNumQueries(0):
            self.assertEqual(appearance(request), {"clinic_theme": "light"})

    def test_saved_dark_theme_applies_to_all_signed_in_pages_and_next_login(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("user_settings:settings"), {"dark_mode": "on"}, follow=True)
        self.assertContains(response, "Your preferences have been saved.")
        for name in (*self.pages, "login:admin_password_reset"):
            with self.subTest(page=name):
                self.assertContains(self.client.get(reverse(name)), 'data-theme="dark"')
        self.client.post(reverse("logout"))
        self.assertContains(self.client.get(reverse("login:login")), 'data-theme="light"')
        self.client.post(reverse("login:login"), {"university_id": self.admin.school_id, "password": "test-password"})
        self.assertContains(self.client.get(reverse("home:home")), 'data-theme="dark"')

    def test_theme_is_account_scoped_and_can_be_turned_off_without_javascript(self):
        UserSettings.objects.create(user=self.admin, dark_mode=True)
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("home:home")), 'data-theme="light"')
        self.client.post(reverse("user_settings:settings"), {"dark_mode": "on", "user": self.admin.pk})
        response = self.client.post(reverse("user_settings:settings"), {}, follow=True)
        self.assertContains(response, 'data-theme="light"')
        self.assertFalse(UserSettings.objects.get(user=self.user).dark_mode)
        self.assertTrue(UserSettings.objects.get(user=self.admin).dark_mode)

    def test_profile_success_message_is_displayed_once_and_content_is_escaped(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile:profile"), {"phone_number": "09000000001", "home_address": "Fictional Cebu", "bio": '<script>alert("test")</script>'}, follow=True)
        self.assertContains(response, "Your profile has been saved.")
        self.assertContains(response, 'role="status"')
        self.assertNotContains(response, '<script>alert("test")</script>')
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(self.client.get(reverse("profile:profile")), "Your profile has been saved.")

    def test_profile_copy_and_fields_match_actual_model_ownership(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile:profile"))
        self.assertContains(response, "contact phone, home address and non-clinical bio")
        self.assertContains(response, 'id="id_phone_number"')
        self.assertNotContains(response, 'id="id_full_name"')
        self.assertNotContains(response, 'name="date_of_birth"')
        self.assertNotContains(self.client.get(reverse("home:home")), "Update your name, age")

    def test_form_errors_have_summary_links_invalid_fields_and_help_references(self):
        self.client.force_login(self.user)
        UserSettings.objects.create(user=self.user, dark_mode=True)
        response = self.client.post(reverse("profile:profile"), {"phone_number": "1" * 31})
        self.assertContains(response, 'id="form-errors"')
        self.assertContains(response, 'href="#id_phone_number"')
        self.assertContains(response, 'data-theme="dark"')
        self.assertNotContains(response, "Your profile has been saved.")
        markup = PageMarkup(response.content.decode())
        ids = {attrs["id"] for tag, attrs in markup.elements if "id" in attrs}
        phone = next(attrs for tag, attrs in markup.elements if attrs.get("id") == "id_phone_number")
        self.assertEqual(phone["aria-invalid"], "true")
        self.assertTrue(all(reference in ids for reference in phone["aria-describedby"].split()))
        self.assertFalse(Profile.objects.filter(user=self.user).exists())

    def test_login_errors_keep_correct_label_target_and_never_echo_password(self):
        response = self.client.post(reverse("login:login"), {"university_id": self.user.school_id, "password": "Wrong-secret-12345"})
        self.assertContains(response, 'for="university_id"')
        self.assertContains(response, 'id="form-errors"')
        self.assertNotContains(response, "Wrong-secret-12345")

    def test_email_preference_is_honest_and_persists_without_delivery(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("user_settings:settings"), {"email_notifications": "on"}, follow=True)
        self.assertContains(response, "Email delivery is not configured.")
        self.assertContains(response, "No notifications will be sent")
        self.assertTrue(UserSettings.objects.get(user=self.user).email_notifications)

    def test_settings_post_still_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.get(reverse("user_settings:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.post(reverse("user_settings:settings"), {"dark_mode": "on"}).status_code, 403)
        self.assertFalse(UserSettings.objects.filter(user=self.user).exists())


class RoleDashboardTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()

    def test_role_dashboards_only_link_to_available_permitted_tasks(self):
        for user, heading in ((self.admin, "ADMIN WORKSPACE"), (self.patient.patient, "PATIENT WORKSPACE"), (self.provider.provider, "PROVIDER WORKSPACE")):
            self.client.force_login(user)
            response = self.client.get(reverse("home:home"))
            self.assertContains(response, heading)
            markup = PageMarkup(response.content.decode())
            for tag, attrs in markup.elements:
                if tag == "a" and attrs.get("href", "").startswith("/"):
                    with self.subTest(role=user.user_type, target=attrs["href"]):
                        resolve(attrs["href"])
                        self.assertEqual(self.client.get(attrs["href"]).status_code, 200)
            for unavailable in ("/clinical/", "/billing/", "/joins/"):
                self.assertNotContains(response, f'href="{unavailable}"')
            if user.user_type == "Admin":
                self.assertContains(response, "Inspect accounts")
                self.assertContains(response, "does not grant clinical access")
            else:
                self.assertNotContains(response, "Inspect accounts")
                self.assertNotContains(response, 'href="/login/reset-password/"')
            if user.pk == self.patient.pk:
                self.assertContains(response, 'href="/appointments/"')
            else:
                self.assertNotContains(response, 'href="/appointments/"')

    def test_dashboard_only_discloses_own_account_not_other_patients_or_clinical_notes(self):
        for user in (self.admin, self.patient.patient, self.provider.provider):
            self.client.force_login(user)
            response = self.client.get(reverse("home:home"))
            self.assertContains(response, user.school_id)
            for other in (self.admin, self.patient.patient, self.provider.provider):
                if other.pk != user.pk:
                    self.assertNotContains(response, other.school_id)
            self.assertNotContains(response, self.record.chief_complaint)

    def test_unknown_affiliation_is_not_invented(self):
        Patient.objects.filter(pk=self.patient.pk).update(affiliation=None)
        self.client.force_login(self.patient.patient)
        self.assertContains(self.client.get(reverse("home:home")), "Awaiting verification")

    def test_inactive_unverified_and_nurse_provider_dashboards(self):
        self.client.force_login(self.provider.provider)
        for designation, active in (("Physician", False), ("Unverified", True), ("Nurse", True)):
            Provider.objects.filter(pk=self.provider.pk).update(provider_type=designation, is_active=active)
            response = self.client.get(reverse("home:home"))
            self.assertContains(response, designation)
            if designation == "Nurse":
                self.assertContains(response, "Nurses will not finalize consultations or issue prescriptions")
            else:
                self.assertContains(response, "Not activated for clinical work")

    def test_admin_patient_and_provider_profiles_do_not_change_primary_workspace(self):
        Patient.objects.create(patient=self.admin, affiliation="Staff")
        Provider.objects.create(provider=self.admin, provider_type="Physician", is_active=True)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("home:home"))
        self.assertContains(response, "ADMIN WORKSPACE")
        self.assertContains(response, "Staff")
        self.assertContains(response, "Physician")
        self.assertTrue(response.context["provider_ready"])
