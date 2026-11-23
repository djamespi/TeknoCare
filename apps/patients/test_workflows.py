from datetime import date, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.clinical.models import MedicalRecord
from apps.common.test_data import clinic_data
from apps.providers.models import Provider
from apps.register.models import User
from apps.university.models import Department

from .models import Affiliation, Patient, PatientAllergy
from .services import save_allergy, save_emergency_contact, update_affiliation


class PatientWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.doctor, cls.slot, cls.record = clinic_data()
        cls.other_user = User.objects.create_user(
            "TEST-OTHER", "other@example.invalid", fname="Other", lname="Patient"
        )
        cls.other_patient = Patient.objects.create(patient=cls.other_user, affiliation=Affiliation.STAFF)
        cls.contact = cls.patient.emergency_contacts.create(
            full_name="Fictional First Contact", relationship="Sibling", phone_number="09000000001", is_primary=True
        )

    def intake_data(self, affiliation):
        return {
            "school_id": f"00-{affiliation}", "first_name": "Fictional", "last_name": "Intake",
            "email": f"new-{affiliation}@example.invalid", "password1": "Meadow-Trail-846!",
            "password2": "Meadow-Trail-846!", "affiliation": affiliation, "confirm": "on",
        }

    def contact_data(self):
        return {
            "full_name": "Fictional New Contact", "relationship": "Parent", "phone_number": "09000000002",
            "is_primary": "on",
        }

    def test_owner_birth_date_and_age_stay_scoped_under_forged_payload(self):
        self.client.force_login(self.patient.patient)
        url = reverse("patients:birth_date")
        self.assertContains(self.client.get(reverse("patients:details")), "Allergies are not documented.")
        self.assertIsNone(Patient.objects.get(pk=self.patient.pk).date_of_birth)
        tomorrow = timezone.localdate() + timedelta(days=1)
        response = self.client.post(url, {"date_of_birth": tomorrow.isoformat()})
        self.assertContains(response, "Birth date cannot be in the future.")
        dob = date(timezone.localdate().year - 20, 1, 1)
        response = self.client.post(url, {
            "date_of_birth": dob.isoformat(), "patient_id": self.other_patient.pk, "affiliation": Affiliation.STAFF,
        }, follow=True)
        self.assertContains(response, "<dd>20</dd>", html=True)
        self.patient.refresh_from_db()
        self.other_patient.refresh_from_db()
        self.assertEqual((self.patient.date_of_birth, self.patient.affiliation), (dob, Affiliation.STUDENT))
        self.assertIsNone(self.other_patient.date_of_birth)
        self.assertTrue(AuditLog.objects.filter(actor_user=self.patient.patient, target_table="patient",
            target_record_id=self.patient.pk, action_performed="Patient birth date updated").exists())

    def test_contact_switch_edit_and_removal_only_affect_own_rows(self):
        self.client.force_login(self.patient.patient)
        other_contact = self.other_patient.emergency_contacts.create(
            full_name="Private Other Contact", relationship="Parent", phone_number="09000000003", is_primary=True
        )
        self.assertNotContains(self.client.get(reverse("patients:details")), other_contact.full_name)
        for route in ("contact_edit", "contact_remove"):
            foreign_url = reverse(f"patients:{route}", args=[other_contact.pk])
            self.assertEqual(self.client.get(foreign_url).status_code, 404)
            self.assertEqual(self.client.post(foreign_url, self.contact_data()).status_code, 404)

        response = self.client.post(reverse("patients:contact_create"), {
            **self.contact_data(), "patient_id": self.other_patient.pk,
        })
        self.assertRedirects(response, reverse("patients:details"))
        primary = self.patient.emergency_contacts.get(is_primary=True)
        self.assertEqual(primary.full_name, self.contact_data()["full_name"])
        self.contact.refresh_from_db()
        other_contact.refresh_from_db()
        self.assertFalse(self.contact.is_primary)
        self.assertTrue(other_contact.is_primary)
        response = self.client.post(reverse("patients:contact_edit", args=[self.contact.pk]), {
            **self.contact_data(), "full_name": "Fictional Restored Primary",
        })
        self.assertRedirects(response, reverse("patients:details"))
        self.assertEqual(self.patient.emergency_contacts.get(is_primary=True).pk, self.contact.pk)
        remove_url = reverse("patients:contact_remove", args=[self.contact.pk])
        self.assertContains(self.client.get(remove_url), "Remove emergency contact")
        self.assertTrue(self.patient.emergency_contacts.filter(pk=self.contact.pk).exists())
        self.assertRedirects(self.client.post(remove_url), reverse("patients:details"))
        self.assertFalse(self.patient.emergency_contacts.filter(is_primary=True).exists())
        self.assertTrue(self.patient.emergency_contacts.filter(pk=primary.pk).exists())

    def test_failed_primary_replacement_preserves_old_primary_and_audit(self):
        with self.assertRaises(ValidationError):
            save_emergency_contact(
                actor=self.patient.patient, full_name=" ", relationship="Parent", phone_number="0900", is_primary=True
            )
        self.assertEqual(self.patient.emergency_contacts.get(is_primary=True).pk, self.contact.pk)
        self.assertFalse(AuditLog.objects.exists())

    def test_mutation_requires_csrf_and_sign_in(self):
        url = reverse("patients:contact_create")
        self.assertEqual(self.client.post(url, self.contact_data()).status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.patient.patient)
        self.assertEqual(client.get(url).status_code, 200)
        self.assertEqual(client.post(url, self.contact_data()).status_code, 403)
        self.assertEqual(self.patient.emergency_contacts.count(), 1)

    def test_intake_list_and_writes_require_admin_even_for_providers(self):
        routes = [
            ("list", []), ("create", []), ("account_lookup", []), ("attach", [self.doctor.pk]),
            ("affiliation", [self.patient.pk]), ("identity", [self.patient.pk]),
        ]
        for user in (self.patient.patient, self.doctor.provider):
            self.client.force_login(user)
            for route, args in routes:
                with self.subTest(role=user.user_type, route=route):
                    url = reverse(f"patient_intake:{route}", args=args)
                    self.assertEqual(self.client.get(url).status_code, 403)
                    self.assertEqual(self.client.post(url, self.intake_data(Affiliation.FACULTY)).status_code, 403)

    def test_admin_intake_creates_all_supported_affiliations_without_role_injection(self):
        self.client.force_login(self.admin)
        url = reverse("patient_intake:create")
        unconfirmed = self.intake_data(Affiliation.STUDENT)
        del unconfirmed["confirm"]
        self.assertContains(self.client.post(url, unconfirmed), "This field is required.")
        for affiliation in Affiliation.values:
            with self.subTest(affiliation=affiliation):
                data = self.intake_data(affiliation)
                response = self.client.post(url, {**data, "user_type": "Admin", "account_status": "Suspended"})
                self.assertRedirects(response, reverse("patient_intake:list"))
                account = User.objects.get(school_id=data["school_id"])
                self.assertEqual((account.email, account.user_type, account.account_status),
                    (data["email"].lower(), User.UserType.PATIENT, User.AccountStatus.ACTIVE))
                self.assertTrue(account.check_password(data["password1"]))
                self.assertEqual(account.patient_profile.affiliation, affiliation)
                self.assertIsNone(account.patient_profile.date_of_birth)
                self.assertFalse(account.patient_profile.allergies.exists())

    def test_admin_attaches_existing_provider_and_admin_without_role_changes(self):
        self.client.force_login(self.admin)
        for account in (self.admin, self.doctor.provider):
            lookup = self.client.get(reverse("patient_intake:account_lookup"), {"school_id": account.school_id})
            url = reverse("patient_intake:attach", args=[account.pk])
            self.assertContains(lookup, url)
            self.assertFalse(Patient.objects.filter(pk=account.pk).exists())
            self.assertRedirects(self.client.post(url, {"affiliation": Affiliation.FACULTY, "confirm": "on"}),
                reverse("patient_intake:list"))
            patient = Patient.objects.get(pk=account.pk)
            self.assertEqual(patient.patient.user_type, account.user_type)
            self.assertEqual(patient.patient.password_hash, account.password_hash)
            self.assertRedirects(self.client.post(url, {"affiliation": Affiliation.STUDENT, "confirm": "on"}),
                reverse("patient_intake:affiliation", args=[account.pk]))
            patient.refresh_from_db()
            self.assertEqual(patient.affiliation, Affiliation.FACULTY)
        self.client.force_login(self.doctor.provider)
        self.assertContains(self.client.get(reverse("patients:details")), "Faculty")

    def test_admin_can_correct_unknown_affiliation_and_preserve_snapshots(self):
        Patient.objects.filter(pk=self.patient.pk).update(affiliation=None)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("patient_intake:list"), {"q": "Test Student", "affiliation": "unknown"})
        self.assertContains(response, "Awaiting review")
        self.assertContains(response, self.patient.patient.school_id)
        self.assertNotContains(response, self.other_user.school_id)
        self.assertNotContains(response, self.contact.full_name)
        self.assertNotContains(response, self.record.chief_complaint)
        url = reverse("patient_intake:affiliation", args=[self.patient.pk])
        self.assertRedirects(self.client.post(url, {"affiliation": Affiliation.STAFF, "confirm": "on"}),
            reverse("patient_intake:list"))
        self.patient.refresh_from_db()
        self.record.refresh_from_db()
        self.assertEqual(self.patient.affiliation, Affiliation.STAFF)
        self.assertEqual(self.record.affiliation_at_visit, Affiliation.STUDENT)
        self.assertContains(self.client.post(url, {"affiliation": "", "confirm": "on"}), "This field is required.")

    def test_inactive_department_may_be_retained_but_cannot_be_newly_assigned(self):
        department = Department.objects.create(code="OLD", name="Fictional old department", is_active=False)
        Patient.objects.filter(pk=self.patient.pk).update(department=department)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("patient_intake:affiliation", args=[self.patient.pk]), {
            "affiliation": Affiliation.STAFF, "department": department.pk, "confirm": "on",
        })
        self.assertRedirects(response, reverse("patient_intake:list"))
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.department_id, department.pk)
        with self.assertRaises(ValidationError):
            update_affiliation(actor=self.admin, patient_id=self.other_patient.pk,
                affiliation=Affiliation.STAFF, department=department)
        self.other_patient.refresh_from_db()
        self.assertIsNone(self.other_patient.department_id)

    def test_identity_correction_validates_duplicates_and_keeps_account_roles_and_links(self):
        self.client.force_login(self.admin)
        account = self.patient.patient
        url = reverse("patient_intake:identity", args=[account.pk])
        data = {"school_id": self.other_user.school_id, "first_name": "Casey", "last_name": "Revised",
            "email": "REVISED@example.invalid", "confirm": "on", "user_type": "Admin"}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        account.refresh_from_db()
        self.assertNotEqual(account.school_id, self.other_user.school_id)
        self.assertRedirects(self.client.post(url, {**data, "school_id": " 001-AbC "}),
            reverse("patient_intake:list"))
        account.refresh_from_db()
        self.assertEqual((account.school_id, account.email, account.user_type),
            ("001-AbC", "revised@example.invalid", User.UserType.PATIENT))
        self.assertEqual(Patient.objects.get(pk=account.pk).affiliation, Affiliation.STUDENT)
        self.assertEqual(self.record.patient_id, account.pk)
        self.assertTrue(AuditLog.objects.filter(actor_user=self.admin, target_table="user",
            action_performed="Patient account identity corrected", target_record_id=account.pk).exists())

    def test_clinical_allergy_workflow_is_assigned_and_visible_to_owner_only(self):
        self.client.force_login(self.doctor.provider)
        lookup_url = reverse("patients:allergy_lookup")
        detail_url = reverse("patients:clinical_allergies", args=[self.patient.pk])
        create_url = reverse("patients:allergy_create", args=[self.patient.pk])
        denied_url = reverse("patients:allergy_create", args=[self.other_patient.pk])
        unassigned = self.client.get(lookup_url, {"school_id": self.other_user.school_id})
        missing = self.client.get(lookup_url, {"school_id": "NONEXISTENT"})
        self.assertEqual(unassigned.context["form"].non_field_errors(), missing.context["form"].non_field_errors())
        self.assertEqual(self.client.get(create_url).status_code, 404)
        MedicalRecord.objects.create(patient=self.patient, provider=self.doctor, chief_complaint="Fictional draft")
        self.assertRedirects(self.client.get(lookup_url, {"school_id": self.patient.patient.school_id}), detail_url)
        values = {"allergen": "Fictional allergen", "reaction": "<script>fictional</script>", "severity": "Mild"}
        self.assertEqual(self.client.post(denied_url, values).status_code, 404)
        self.assertRedirects(self.client.post(create_url, {**values, "patient_id": self.other_patient.pk,
            "actor_user": self.admin.pk}), detail_url)
        allergy = self.patient.allergies.get()
        self.assertEqual(allergy.severity, PatientAllergy.Severity.MILD)
        self.assertRedirects(self.client.post(reverse("patients:allergy_edit", args=[self.patient.pk, allergy.pk]), {
            **values, "severity": "Moderate",
        }), detail_url)
        recorded_at = allergy.recorded_at
        allergy.refresh_from_db()
        self.assertEqual(allergy.recorded_at, recorded_at)
        self.assertEqual(allergy.severity, PatientAllergy.Severity.MODERATE)
        self.assertEqual(AuditLog.objects.filter(actor_user=self.doctor.provider, target_table="patient_allergy",
            target_record_id=allergy.pk).count(), 2)
        self.client.force_login(self.patient.patient)
        details = self.client.get(reverse("patients:details"))
        self.assertContains(details, allergy.allergen)
        self.assertNotContains(details, values["reaction"])
        self.assertNotContains(details, "Record allergy")
        self.assertEqual(self.client.post(create_url, values).status_code, 403)
        self.client.force_login(self.other_user)
        self.assertNotContains(self.client.get(reverse("patients:details")), allergy.allergen)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(detail_url).status_code, 403)
        self.assertEqual(self.client.post(create_url, values).status_code, 403)

    def test_clinical_services_reject_self_editing_and_stale_provider_eligibility(self):
        doctor_account = self.doctor.provider
        doctor_patient = Patient.objects.create(patient=doctor_account, affiliation=Affiliation.STAFF)
        MedicalRecord.objects.create(patient=doctor_patient, provider=self.doctor, chief_complaint="Fictional draft")
        MedicalRecord.objects.create(patient=self.patient, provider=self.doctor, chief_complaint="Fictional draft")
        values = {"actor": doctor_account, "allergen": "Fictional", "reaction": "", "severity": "Unknown"}
        with self.assertRaises(PermissionDenied):
            save_allergy(patient_id=doctor_patient.pk, **values)
        Provider.objects.filter(pk=self.doctor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            save_allergy(patient_id=self.patient.pk, **values)
        self.assertFalse(PatientAllergy.objects.exists())

    def test_nurse_can_record_for_todays_draft_but_not_an_unrelated_patient(self):
        account = User.objects.create_user("TEST-NURSE", "nurse@example.invalid", user_type=User.UserType.PROVIDER)
        Provider.objects.create(provider=account, provider_type=Provider.Type.NURSE, is_active=True)
        MedicalRecord.objects.create(patient=self.patient, provider=self.doctor, chief_complaint="Fictional draft")
        values = {"actor": account, "allergen": "Fictional", "reaction": "", "severity": "Unknown"}
        with self.assertRaises(PermissionDenied):
            save_allergy(patient_id=self.other_patient.pk, **values)
        save_allergy(patient_id=self.patient.pk, **values)
        self.assertTrue(self.patient.allergies.exists())
