from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.clinical.models import MedicalRecord
from apps.common.test_data import clinic_data
from apps.patients.models import Patient
from apps.prescriptions.models import Medication, Prescription
from apps.register.models import User


class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.provider, cls.slot, _ = clinic_data()
        cls.other = User.objects.create_user("PORTAL-OTHER", "portal-other@example.invalid", "user-password")
        Patient.objects.create(patient=cls.other, affiliation="Student")
        now = timezone.now()
        cls.summary = MedicalRecord.objects.create(
            patient=cls.patient, provider=cls.provider, chief_complaint="Fictional visit summary",
            examination_notes="PRIVATE_EXAMINATION", status="Finalized", visited_at=now, finalized_at=now,
        )

    def request_action(self, name, body, *, client=None, csrf=None):
        client = client or self.client
        headers = {"X-CSRFToken": csrf} if csrf else {}
        return client.post(reverse("portal:action", args=[name]), body, content_type="application/json", headers=headers)

    def assert_portal_patch(self, response, tables):
        self.assertEqual(response.status_code, 200, response.content)
        patch = response.json()["patch"]["db"]
        self.assertEqual(set(patch), set(tables))
        full = self.client.get(reverse("portal:snapshot")).json()["db"]
        self.assertEqual(patch, {table: full[table] for table in tables})
        return patch

    def test_anonymous_snapshot_and_login_require_session_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        session = client.get(reverse("portal:snapshot"))
        self.assertIsNone(session.json()["db"])
        self.assertIn("no-store", session["Cache-Control"])
        credentials = {"university_id": self.patient.patient.school_id, "password": "test-password"}
        self.assertEqual(self.request_action("login", credentials, client=client).status_code, 403)
        self.assertEqual(self.request_action("login", credentials, client=client, csrf=session.json()["csrf"]).status_code, 200)
        signed_in = client.get(reverse("portal:snapshot"))
        self.assertEqual(signed_in.json()["actor"], self.patient.pk)
        self.assertNotContains(signed_in, "password_hash")

    def test_snapshot_never_releases_other_contacts_or_private_notes_to_patient(self):
        self.client.force_login(self.patient.patient)
        response = self.client.get(reverse("portal:snapshot"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.other.school_id)
        self.assertNotContains(response, self.provider.provider.email)
        self.assertNotContains(response, self.summary.examination_notes)
        self.assertIn(self.summary.pk, [row["record_id"] for row in response.json()["db"]["medical_record"]])

    def test_booking_and_cancellation_use_existing_write_rules(self):
        self.client.force_login(self.patient.patient)
        slot = next(slot for slot in self.client.get(reverse("portal:snapshot")).json()["db"]["slot"] if slot["bookable"])
        booking = self.request_action("book", {"slot_id": slot["slot_id"], "version": slot["version"], "reason": "Fictional visit"})
        tables = {"appointment", "slot", "clinic_room", "provider", "user"}
        self.assert_portal_patch(booking, tables)
        booked = Appointment.objects.get(pk=booking.json()["result"])
        self.assertEqual(booked.patient_id, self.patient.pk)
        self.client.force_login(self.other)
        self.assertEqual(self.request_action("cancel-booking", {"id": booked.pk}).status_code, 403)
        self.client.force_login(self.patient.patient)
        self.assert_portal_patch(self.request_action("cancel-booking", {"id": booked.pk}), tables)
        booked.refresh_from_db()
        self.assertEqual(booked.status, Appointment.Status.CANCELED)

    def test_account_and_reference_actions_refresh_only_their_changed_tables(self):
        self.client.force_login(self.patient.patient)
        added = self.request_action("contact", {
            "full_name": " Fictional Contact ", "relationship": "Parent",
            "phone_number": "09123456789", "is_primary": True,
        })
        contacts = self.assert_portal_patch(added, {"emergency_contact"})["emergency_contact"]
        contact = next(row for row in contacts if row["full_name"] == "Fictional Contact")
        removed = self.request_action("remove-contact", {"id": contact["contact_id"]})
        contacts = self.assert_portal_patch(removed, {"emergency_contact"})["emergency_contact"]
        self.assertNotIn(contact["contact_id"], [row["contact_id"] for row in contacts])

        self.client.force_login(self.admin)
        saved = self.request_action("save-reference", {"table": "department", "entry": {
            "code": "PATCH", "name": "Patch example", "is_active": True,
        }})
        self.assert_portal_patch(saved, {"department", "audit_log"})

    def test_provider_and_admin_reads_follow_existing_chart_boundaries(self):
        self.client.force_login(self.provider.provider)
        response = self.client.get(reverse("portal:snapshot"))
        self.assertContains(response, self.summary.examination_notes)
        self.assertNotContains(response, self.other.school_id)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("portal:snapshot"))
        self.assertNotContains(response, self.summary.examination_notes)
        self.assertEqual(response.json()["db"]["medical_record"], [])

    def test_clinical_commands_require_current_version_and_finalize_after_issuing(self):
        draft = MedicalRecord.objects.create(
            patient=self.patient, provider=self.provider, chief_complaint="Fictional draft",
            examination_notes="Fictional note", treatment_plan="Fictional plan",
        )
        medication = Medication.objects.create(
            medication_code="PORTAL-MED", generic_name="Fictional item", strength="Demo strength", dosage_form="Demo form",
        )
        self.client.force_login(self.provider.provider)

        def snapshot():
            return self.client.get(reverse("portal:snapshot")).json()["db"]

        def record_version():
            return next(row["version"] for row in snapshot()["medical_record"] if row["record_id"] == draft.pk)

        original = record_version()
        vital = self.request_action("save-vitals", {"id": draft.pk, "version": original, "measurements": {"pulse_bpm": 74}})
        updated = self.assert_portal_patch(vital, {"medical_record", "vital_sign"})
        self.assertNotEqual(next(row["version"] for row in updated["medical_record"] if row["record_id"] == draft.pk), original)
        self.assertEqual(draft.vital_signs.count(), 1)
        stale = self.request_action("save-notes", {"id": draft.pk, "version": original, "notes": {"symptoms": "Fictional entry"}})
        self.assertEqual(stale.status_code, 400)
        item = self.request_action("add-prescription-item", {"id": draft.pk, "item": {
            "medication_id": medication.pk, "dose": "Demo dose", "route": "Demo route", "frequency": "Demo frequency",
            "duration_days": 1, "quantity": 1, "quantity_unit": "Demo unit",
        }})
        prescription_tables = {"prescription", "prescription_item"}
        prescription_patch = self.assert_portal_patch(item, prescription_tables)
        prescription = prescription_patch["prescription"][0]
        removed = self.request_action("delete-prescription-item", {
            "id": prescription_patch["prescription_item"][0]["item_id"], "version": prescription["version"],
        })
        prescription_patch = self.assert_portal_patch(removed, prescription_tables)
        self.assertEqual(prescription_patch["prescription_item"], [])
        prescription = prescription_patch["prescription"][0]
        item = self.request_action("add-prescription-item", {
            "id": draft.pk, "prescription_id": prescription["prescription_id"], "version": prescription["version"],
            "item": {"medication_id": medication.pk, "dose": "Demo dose", "route": "Demo route",
                     "frequency": "Demo frequency", "duration_days": 1, "quantity": 1, "quantity_unit": "Demo unit"},
        })
        prescription = self.assert_portal_patch(item, prescription_tables)["prescription"][0]
        self.assertEqual(self.request_action("finalize", {"id": draft.pk, "version": record_version()}).status_code, 400)
        issued = self.request_action("prescription-status", {
            "id": prescription["prescription_id"], "version": prescription["version"], "operation": "issue",
        })
        self.assert_portal_patch(issued, prescription_tables)
        self.assertEqual(Prescription.objects.get(record=draft).status, Prescription.Status.ISSUED)
        finalized = self.request_action("finalize", {"id": draft.pk, "version": record_version()})
        self.assertEqual(finalized.status_code, 200, finalized.content)
        draft.refresh_from_db()
        self.assertEqual(draft.status, MedicalRecord.Status.FINALIZED)
