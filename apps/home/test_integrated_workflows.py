from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection, connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.billing.models import AcademicTerm, StudentCharge
from apps.billing.services import create_charge, simulate_posting
from apps.clinical.consultation import consultation_version, finalize_consultation
from apps.clinical.models import Diagnosis, MedicalRecord
from apps.common.test_data import clinic_data
from apps.prescriptions.models import Medication
from apps.providers.models import Provider
from apps.register.models import User


PASSWORD = "Integrated-fixture-pass-491!"
NOTES = {
    "notes-chief_complaint": "Fictional demo visit",
    "notes-examination_notes": "Private examination marker",
    "notes-treatment_plan": "Fictional follow-up plan",
}


def open_term():
    return AcademicTerm.objects.create(
        academic_year="2026-2027", semester="Integration", start_date=date(2026, 8, 1),
        end_date=date(2027, 7, 31), is_open_for_charges=True,
    )


class ClinicJourneyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, _, cls.doctor, cls.slot, _ = clinic_data()
        cls.nurse = cls.provision_provider("Nurse")
        cls.dentist = cls.provision_provider("Dentist")
        cls.term = open_term()
        cls.medication = Medication.objects.create(medication_code="INTEGRATION", generic_name="Fictional demo item",
            strength="Training only", dosage_form="Prototype")
        cls.diagnosis = Diagnosis.objects.create(coding_system="Prototype", code="INTEGRATION", description="Fictional finding")

    @staticmethod
    def provision_provider(designation):
        account = User.objects.create_user(f"FLOW-{designation.upper()}", f"{designation.lower()}@example.invalid",
            user_type=User.UserType.PROVIDER)
        return Provider.objects.create(provider=account, provider_type=designation, is_active=True)

    def session(self, account):
        session = Client()
        session.force_login(account)
        return session

    def save_notes(self, client, workspace):
        page = client.get(workspace)
        payload = {**NOTES, "action": "notes", "notes-expected_version": page.context["notes_form"].initial["expected_version"],
            "notes-diagnoses": [self.diagnosis.pk], "notes-primary_diagnosis": self.diagnosis.pk}
        self.assertRedirects(client.post(workspace, payload), workspace, fetch_redirect_response=False)

    def finalize(self, client, workspace):
        form = client.get(workspace).context["finalize_form"]
        data = {"action": "finalize", "finalize-confirm": "on", "finalize-expected_version": form.initial["expected_version"]}
        self.assertRedirects(client.post(workspace, data), workspace, fetch_redirect_response=False)

    def test_student_booking_to_released_care_and_simulated_tuition(self):
        student = Client()
        signup = {
            "university_id": "FLOW-001", "first_name": "Fictional", "last_name": "Student", "email": "flow@example.invalid",
            "emergency_contact_name": "Fictional Contact", "emergency_contact_relationship": "Relative",
            "emergency_contact": "09000000001", "password1": PASSWORD, "password2": PASSWORD,
        }
        self.assertRedirects(student.post(reverse("register:register"), signup), reverse("login:login"))
        self.assertRedirects(student.post(reverse("login:login"), {"university_id": "FLOW-001", "password": PASSWORD}),
            reverse("home:home"))
        account = User.objects.get(school_id="FLOW-001")
        contacts = {"full_name": "Another Fictional Contact", "relationship": "Relative", "phone_number": "09000000002"}
        self.assertRedirects(student.post(reverse("patients:contact_create"), contacts), reverse("patients:details"))
        self.assertEqual(account.patient_profile.emergency_contacts.count(), 2)

        browse = reverse("booking:browse")
        self.assertContains(student.get(browse), reverse("booking:book", args=[self.slot.pk]))
        book = reverse("booking:book", args=[self.slot.pk])
        payload = {"expected_version": self.slot.version, "reason_for_visit": "Fictional appointment"}
        self.assertEqual(student.post(book, payload).status_code, 302)
        first = Appointment.objects.get(patient_id=account.pk)
        self.assertEqual(student.post(reverse("booking:cancel", args=[first.pk])).status_code, 302)
        first.refresh_from_db()
        self.assertEqual(first.status, Appointment.Status.CANCELED)
        self.assertEqual(student.post(book, payload).status_code, 302)
        booking = Appointment.objects.get(patient_id=account.pk, status=Appointment.Status.SCHEDULED)

        admin = self.session(self.admin)
        reception = reverse("reception:appointment", args=[booking.pk])
        with patch("django.utils.timezone.now", return_value=self.slot.start_time):
            self.assertRedirects(admin.post(reception, {"action": "check_in"}), reception, fetch_redirect_response=False)
            opened = admin.post(reception, {"action": "open", "provider": self.doctor.pk})
        visit = MedicalRecord.objects.get(appointment=booking)
        self.assertRedirects(opened, reverse("reception:encounter", args=[visit.pk]), fetch_redirect_response=False)
        summary = reverse("patients:visit_summary", args=[visit.pk])
        self.assertEqual(student.get(summary).status_code, 404)

        workspace = reverse("consultation:workspace", args=[visit.pk])
        nurse = self.session(self.nurse.provider)
        triage = nurse.get(workspace)
        version = triage.context["vitals_form"].initial["expected_version"]
        self.assertIsNone(triage.context["notes_form"])
        self.assertEqual(nurse.post(workspace, {"action": "vitals", "vitals-expected_version": version,
            "vitals-pulse_bpm": "75"}).status_code, 302)
        self.assertEqual(visit.vital_signs.get().recorded_by_user_id, self.nurse.pk)

        doctor = self.session(self.doctor.provider)
        self.save_notes(doctor, workspace)
        referral = reverse("consultation:referral_create", args=[visit.pk])
        self.assertEqual(doctor.post(referral, {"destination": "Fictional referral desk",
            "reason": "Training instructions"}).status_code, 302)
        rx_encounter = reverse("prescriptions:encounter", args=[visit.pk])
        self.assertEqual(doctor.post(rx_encounter).status_code, 302)
        prescription = visit.prescriptions.get()
        item_add = reverse("prescriptions:item_create", args=[visit.pk, prescription.pk])
        item_version = doctor.get(item_add).context["form"].initial["expected_version"]
        self.assertEqual(doctor.post(item_add, {"expected_version": item_version, "medication": self.medication.pk,
            "dose": "Demo quantity", "route": "Demo route", "frequency": "Demo schedule", "duration_days": 1,
            "quantity": "1.00", "quantity_unit": "Demo unit"}).status_code, 302)
        rx_detail = reverse("prescriptions:detail", args=[visit.pk, prescription.pk])
        rx_version = doctor.get(rx_detail).context["version"]
        self.assertEqual(doctor.post(rx_detail, {"action": "issue", "issue-confirm": "on",
            "issue-expected_version": rx_version}).status_code, 302)
        self.finalize(doctor, workspace)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Appointment.Status.COMPLETED)
        released = student.get(summary)
        for visible in ("Fictional finding", "Fictional referral desk", "Fictional demo item"):
            self.assertContains(released, visible)
        self.assertNotContains(released, NOTES["notes-examination_notes"])

        create = reverse("billing:charge_create", args=[visit.pk])
        request_code = admin.get(create).context["form"].initial["request_code"]
        response = admin.post(create, {"request_code": request_code, "term": self.term.pk,
            "description": "Clinic service (prototype)", "amount": "125.50"})
        charge = visit.student_charges.get()
        self.assertEqual(charge.status, StudentCharge.Status.PENDING)
        detail = reverse("billing:charge_detail", args=[charge.pk])
        self.assertRedirects(response, detail, fetch_redirect_response=False)
        self.assertContains(admin.get(reverse("billing:charge_export"), {"term": self.term.pk}), charge.charge_code)
        post = {"action": "post", "post-confirm": "on"}
        for _ in range(2):
            self.assertRedirects(admin.post(detail, post), detail, fetch_redirect_response=False)
        posted_report = admin.get(reverse("audit:reports"), {"term": self.term.pk}).context["charges_page"][0]
        self.assertEqual(posted_report["posted"], Decimal("125.50"))
        self.assertEqual(admin.post(detail, {"action": "void", "void-expected_status": "Posted", "void-confirm": "on",
            "void-reason": "Fictional reconciliation"}).status_code, 302)
        own_charge = reverse("billing:patient_charge_detail", args=[charge.pk])
        self.assertContains(student.get(own_charge), "Voided")
        self.assertContains(admin.get(reverse("audit:history"), {"action": "Simulated tuition reversal confirmed"}),
            "Simulated tuition reversal confirmed")
        self.assertEqual(AuditLog.objects.filter(target_table="student_charge", target_record_id=charge.pk,
            action_performed="Simulated tuition posting acknowledged").count(), 1)

        self.assertEqual(admin.post(reverse("accounts:status", args=[account.pk]),
            {"account_status": "Suspended", "confirm": "on"}).status_code, 302)
        self.assertEqual(student.get(summary).status_code, 302)
        self.assertEqual(StudentCharge.objects.get(pk=charge.pk).status, StudentCharge.Status.VOIDED)

    def test_faculty_staff_and_admin_as_patient_receive_free_care(self):
        admin = self.session(self.admin)
        dentist = self.session(self.dentist.provider)
        attach = reverse("patient_intake:attach", args=[self.admin.pk])
        self.assertEqual(admin.post(attach, {"affiliation": "Staff", "confirm": "on"}).status_code, 302)
        accounts = [(self.admin, "Staff", admin)]
        for affiliation in ("Faculty", "Staff"):
            school_id = f"FLOW-{affiliation.upper()}"
            data = {"school_id": school_id, "first_name": "Prototype", "last_name": affiliation,
                "email": f"flow-{affiliation.lower()}@example.invalid", "affiliation": affiliation,
                "password1": PASSWORD, "password2": PASSWORD}
            self.assertEqual(admin.post(reverse("accounts:personnel_create"), data).status_code, 302)
            user = User.objects.get(school_id=school_id)
            accounts.append((user, affiliation, self.session(user)))

        for user, affiliation, session in accounts:
            with self.subTest(affiliation=affiliation, role=user.user_type):
                walk_in = reverse("reception:walkin_create", args=[user.pk])
                self.assertEqual(admin.post(walk_in, {"provider": self.dentist.pk}).status_code, 302)
                visit = MedicalRecord.objects.get(patient_id=user.pk)
                self.assertEqual(visit.affiliation_at_visit, affiliation)
                workspace = reverse("consultation:workspace", args=[visit.pk])
                self.assertEqual(session.get(workspace).status_code, 403)
                self.save_notes(dentist, workspace)
                self.finalize(dentist, workspace)
                self.assertContains(admin.get(reverse("billing:charge_create", args=[visit.pk])), "visits are free")
                self.assertContains(session.get(reverse("billing:patient_charges")), "visits as Faculty or Staff are free")
                summary = reverse("patients:visit_summary", args=[visit.pk])
                self.assertContains(session.get(summary), "Fictional finding")
                for other, _, other_session in accounts:
                    if other.pk != user.pk:
                        self.assertEqual(other_session.get(summary).status_code, 404)
        self.assertFalse(StudentCharge.objects.exists())


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class FinalizationAndBillingConcurrencyTests(TransactionTestCase):
    available_apps = settings.INSTALLED_APPS

    def race(self, operation):
        gate = Barrier(2, timeout=10)

        def request(_worker):
            close_old_connections()
            try:
                gate.wait()
                return operation()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(request, range(2), timeout=25))

    def test_two_finalizations_write_one_finalized_visit_and_audit_event(self):
        _, patient, doctor, _, _ = clinic_data()
        visit = MedicalRecord.objects.create(patient=patient, provider=doctor,
            chief_complaint="Fictional complaint", symptoms="Fictional symptoms", treatment_plan="Fictional plan")
        version = consultation_version(visit, (), None)

        def finalize():
            try:
                finalize_consultation(actor=doctor.provider, record_id=visit.pk, expected_version=version)
            except PermissionDenied:
                return "already finalized"
            return "finalized"

        self.assertCountEqual(self.race(finalize), ["finalized", "already finalized"])
        visit.refresh_from_db()
        self.assertEqual(visit.status, MedicalRecord.Status.FINALIZED)
        self.assertEqual(AuditLog.objects.filter(target_table="medical_record", target_record_id=visit.pk,
            action_performed="Consultation finalized").count(), 1)

    def test_two_simulated_postings_share_one_reference_and_audit_event(self):
        admin, _, _, _, visit = clinic_data()
        charge = create_charge(record_id=visit.pk, term_id=open_term().pk, description="Fictional service",
            amount=Decimal("125.50"), actor=admin)
        timestamps = self.race(lambda: simulate_posting(charge_id=charge.pk, actor=admin, confirmed=True).posted_at)

        charge.refresh_from_db()
        self.assertEqual(charge.status, StudentCharge.Status.POSTED)
        self.assertEqual(timestamps, [charge.posted_at, charge.posted_at])
        self.assertEqual(charge.billing_reference, f"DEMO-POST-{charge.charge_code}")
        self.assertEqual(AuditLog.objects.filter(target_table="student_charge", target_record_id=charge.pk,
            action_performed="Simulated tuition posting acknowledged").count(), 1)
