from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.appointments.models import Appointment, Slot
from apps.billing.models import AcademicTerm, StudentCharge
from apps.billing.services import record_posting, void_charge
from apps.clinical.models import MedicalRecord, Referral
from apps.common.test_data import clinic_data
from apps.common.test_interface_components import PageMarkup
from apps.patients.models import Affiliation, Patient
from apps.providers.models import Provider
from apps.register.models import User

from .models import AuditLog


# Midnight January 2 in Manila. Fixtures are independent of the test runner's clock.
START = datetime(2025, 1, 1, 16, tzinfo=timezone.utc)
DAY = {"from_date": "2025-01-02", "through_date": "2025-01-02"}


class AuditReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.provider, _, cls.visit = clinic_data()

    def test_viewers_require_admin_and_accept_only_read_requests(self):
        urls = [reverse("audit:history"), reverse("audit:reports")]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        for account in (self.patient.patient, self.provider.provider):
            self.client.force_login(account)
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        setup = self.client.get(reverse("university:management"))
        for url in urls:
            self.assertContains(setup, url)
            self.assertIn("no-store", self.client.get(url)["Cache-Control"])
            for method in (self.client.post, self.client.put, self.client.delete):
                self.assertEqual(method(url).status_code, 405)
        self.assertFalse(AuditLog.objects.exists())

    def test_audit_filters_are_combined_and_pages_keep_filters(self):
        def event(**overrides):
            fields = {
                "actor_user": self.admin, "action_performed": "Encounter reviewed",
                "target_table": "medical_record", "target_record_id": self.visit.pk, "logged_at": START,
            }
            return AuditLog.objects.create(**(fields | overrides))

        matches = [event(logged_at=START + timedelta(minutes=index)) for index in range(16)]
        event(logged_at=START - timedelta(seconds=1))
        event(logged_at=START + timedelta(days=1))
        event(actor_user=self.provider.provider)
        event(action_performed="Clinical encounter viewed")
        event(target_table="referral")
        event(target_record_id=self.visit.pk + 1)
        event(actor_user=None, action_performed="Legacy event")
        self.client.force_login(self.admin)
        url = reverse("audit:history")
        filters = {**DAY, "actor": self.admin.school_id, "action": "REVIEWED",
            "target_table": "medical_record", "target_id": self.visit.pk}
        response = self.client.get(url, filters)
        page = response.context["page_obj"]
        self.assertEqual(page.paginator.count, 16)
        self.assertEqual([row["pk"] for row in page], [event.pk for event in reversed(matches[1:])])
        markup = PageMarkup(response.content.decode())
        next_url = next(attrs["href"] for tag, attrs in markup.elements if tag == "a" and attrs.get("rel") == "next")
        self.assertEqual(parse_qs(urlsplit(next_url).query), {
            **{key: [str(value)] for key, value in filters.items()}, "page": ["2"],
        })
        self.assertEqual(self.client.get(url + next_url).context["page_obj"][0]["pk"], matches[0].pk)
        self.assertContains(response, "2025-01-02 00:15:00")
        self.assertContains(self.client.get(url, {"action": "Legacy event"}), "Unavailable")
        invalid = self.client.get(url, {"from_date": "2025-01-03", "through_date": "2025-01-02"})
        self.assertContains(invalid, "Choose a date on or after From date")
        self.assertEqual(invalid.context["page_obj"].paginator.count, 0)
        self.assertEqual(AuditLog.objects.count(), 23)

    def test_authorized_clinical_read_records_only_access_metadata(self):
        workspace = reverse("consultation:workspace", args=[self.visit.pk])
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(workspace).status_code, 403)
        self.assertFalse(AuditLog.objects.exists())

        self.client.force_login(self.provider.provider)
        result = self.client.get(workspace)
        self.assertContains(result, self.visit.chief_complaint)
        self.assertIn("no-store", result["Cache-Control"])
        event = AuditLog.objects.get()
        self.assertEqual((event.actor_user_id, event.action_performed, event.target_table, event.target_record_id),
            (self.provider.pk, "Clinical encounter viewed", "medical_record", self.visit.pk))

        self.client.force_login(self.admin)
        review = self.client.get(reverse("audit:history"), {"action": "Clinical encounter viewed"})
        self.assertContains(review, "Clinical encounter viewed")
        self.assertNotContains(review, self.visit.chief_complaint)
        self.assertEqual(AuditLog.objects.count(), 1)


class OperationalReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.student, cls.provider, cls.slot, _ = clinic_data()
        cls.term = cls.new_term("First")
        cls.other_term = cls.new_term("Second")

    @staticmethod
    def new_term(semester):
        return AcademicTerm.objects.create(
            academic_year="2024-2025", semester=semester, start_date=date(2024, 12, 1),
            end_date=date(2025, 5, 1), is_open_for_charges=True,
        )

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("audit:reports")

    def new_patient(self, school_id, email, affiliation):
        account = User.objects.create_user(school_id, email, "test-password")
        return Patient.objects.create(patient=account, affiliation=affiliation)

    def new_provider(self, school_id, email):
        account = User.objects.create_user(school_id, email, "test-password",
            fname="Fictional", lname="Provider", user_type=User.UserType.PROVIDER)
        return Provider.objects.create(provider=account, provider_type=Provider.Type.PHYSICIAN, is_active=True)

    def appointment(self, patient, status, start, provider=None):
        slot = Slot.objects.create(provider=provider or self.provider, room=self.slot.room,
            start_time=start, end_time=start + timedelta(minutes=15), is_active=True)
        return Appointment.objects.create(patient=patient, slot=slot, status=status, reason_for_visit="Private appointment reason")

    def visit(self, patient, provider=None, visited_at=START, appointment=None, finalized=False):
        return MedicalRecord.objects.create(patient=patient, provider=provider or self.provider, appointment=appointment,
            visited_at=visited_at, chief_complaint="Private visit note",
            status=MedicalRecord.Status.FINALIZED if finalized else MedicalRecord.Status.DRAFT,
            finalized_at=visited_at if finalized else None)

    def charge(self, visit, amount, term=None, created_at=START):
        return StudentCharge.objects.create(record=visit, term=term or self.term, created_by_user=self.admin,
            description="Private charge line", amount=Decimal(amount), currency_code=settings.CLINIC_CURRENCY_CODE,
            created_at=created_at)

    def referral(self, visit, referred_at=START):
        return Referral.objects.create(record=visit, referred_by_provider=visit.provider, destination="Private referral",
            reason="Private instructions", referred_at=referred_at)

    def test_report_reconciles_source_dates_current_statuses_and_tuition_term(self):
        self.appointment(self.student, Appointment.Status.SCHEDULED, START - timedelta(minutes=20))
        self.appointment(self.student, Appointment.Status.NO_SHOW, START)
        self.appointment(self.student, Appointment.Status.SCHEDULED, START + timedelta(hours=2))
        self.appointment(self.student, Appointment.Status.SCHEDULED, START + timedelta(days=1))
        finalized = self.visit(self.student, finalized=True)
        faculty = self.new_patient("TEST-FACULTY", "faculty@example.invalid", Affiliation.FACULTY)
        staff = self.new_patient("TEST-STAFF", "staff@example.invalid", Affiliation.STAFF)
        faculty_visit = self.visit(faculty)
        self.visit(staff, visited_at=START + timedelta(days=1, seconds=-1))
        self.visit(self.student, visited_at=START - timedelta(seconds=1))
        self.visit(self.student, visited_at=START + timedelta(days=1))
        Patient.objects.filter(pk=faculty.pk).update(affiliation=Affiliation.STUDENT)

        referral = self.referral(faculty_visit)
        referral.status = Referral.Status.COMPLETED
        referral.save(update_fields=["status"])
        self.referral(faculty_visit, referred_at=START + timedelta(days=1))
        self.charge(finalized, "10.10")
        self.charge(finalized, "20.20")
        posted = self.charge(finalized, "33.33")
        record_posting(charge_id=posted.pk, billing_reference="DEMO-REPORT", actor=self.admin)
        voided = self.charge(finalized, "42.00")
        void_charge(charge_id=voided.pk, reason="Correction", actor=self.admin)
        self.charge(finalized, "50.00", term=self.other_term)
        self.charge(finalized, "90.00", created_at=START - timedelta(seconds=1))

        response = self.client.get(self.url, {**DAY, "term": self.term.pk})
        self.assertEqual(dict(response.context["appointment_counts"]), {
            "Scheduled": 1, "Checked in": 0, "Completed": 0, "Canceled": 0, "No show": 1,
        })
        self.assertEqual(dict(response.context["visit_counts"]), {"Draft": 2, "Finalized": 1})
        self.assertEqual(dict(response.context["affiliation_counts"]), {"Student": 1, "Faculty": 1, "Staff": 1, "Unverified": 0})
        self.assertEqual(dict(response.context["referral_counts"]), {"Pending": 0, "Completed": 1, "Canceled": 0})
        workload = response.context["workload_page"][0]
        self.assertEqual((workload["provider_id"], workload["draft"], workload["finalized"], workload["total"]),
            (self.provider.pk, 2, 1, 3))
        grouped = response.context["charges_page"]
        self.assertEqual(grouped.paginator.count, 1)
        self.assertEqual((grouped[0]["lines"], grouped[0]["pending"], grouped[0]["posted"], grouped[0]["voided"]),
            (4, Decimal("30.30"), Decimal("33.33"), Decimal("42.00")))
        self.assertEqual(self.client.get(self.url, DAY).context["charges_page"].paginator.count, 2)
        for private in ("Private appointment reason", "Private visit note", "Private referral", "Private charge line", self.student.patient.school_id):
            self.assertNotContains(response, private)
        self.assertContains(response, "30.30")
        self.assertContains(response, "33.33")
        self.assertContains(response, "42.00")

    def test_report_excludes_only_exact_assessment_accounts_and_their_links(self):
        demo_patient = self.new_patient("JOIN-DEMO-001", "ana@join-demo.example.invalid", Affiliation.STUDENT)
        demo_provider = self.new_provider("JOIN-DEMO-004", "maya@join-demo.example.invalid")
        near_id = self.new_patient("JOIN-DEMO-002", "different@example.invalid", Affiliation.STUDENT)
        near_email = self.new_patient("NEAR-EMAIL", "ben@join-demo.example.invalid", Affiliation.STUDENT)
        self.appointment(demo_patient, Appointment.Status.SCHEDULED, START)
        self.appointment(near_id, Appointment.Status.NO_SHOW, START + timedelta(hours=1))
        demo_appointment = self.appointment(near_email, Appointment.Status.COMPLETED, START + timedelta(hours=2), demo_provider)
        demo_visits = [self.visit(demo_patient), self.visit(near_email, provider=demo_provider),
            self.visit(near_email, appointment=demo_appointment)]
        reassigned = self.visit(near_id, provider=demo_provider)
        self.referral(reassigned)
        reassigned.provider = self.provider
        reassigned.save(update_fields=["provider"])
        included = [reassigned, self.visit(near_email)]
        for visit in [*demo_visits, *included]:
            self.referral(visit)
            self.charge(visit, "100.00")
        result = self.client.get(self.url, DAY)
        self.assertEqual(dict(result.context["appointment_counts"])["No show"], 1)
        self.assertEqual(sum(dict(result.context["appointment_counts"]).values()), 1)
        self.assertEqual(dict(result.context["visit_counts"])["Draft"], 2)
        self.assertEqual(dict(result.context["referral_counts"])["Pending"], 2)
        self.assertEqual(result.context["workload_page"].paginator.count, 1)
        self.assertEqual(result.context["charges_page"][0]["pending"], Decimal("200.00"))
        self.assertNotContains(result, demo_provider.provider.school_id)
        self.assertEqual(MedicalRecord.objects.filter(pk__in=[visit.pk for visit in demo_visits]).count(), 3)

    def test_empty_and_invalid_report_filters(self):
        empty = self.client.get(self.url, DAY)
        self.assertContains(empty, "No provider visits match this date range.")
        self.assertContains(empty, "No tuition charges match this date range and term.")
        self.assertEqual(dict(empty.context["visit_counts"]), {"Draft": 0, "Finalized": 0})
        invalid = self.client.get(self.url, {"from_date": "2025-01-03", "through_date": "2025-01-02"})
        self.assertContains(invalid, "Choose a date on or after From date")
        self.assertNotContains(invalid, "Appointments by status")

    def test_workload_and_charge_tables_paginate_independently(self):
        for index in range(11):
            provider = self.new_provider(f"PAGE-{index:02d}", f"page-{index}@example.invalid")
            visit = self.visit(self.student, provider=provider)
            self.charge(visit, "25.00", term=self.new_term(f"Term {index:02d}"))
        result = self.client.get(self.url, {**DAY, "workload_page": "2", "charges_page": "1"})
        self.assertEqual(len(result.context["workload_page"]), 1)
        self.assertEqual(len(result.context["charges_page"]), 10)
        links = [attrs["href"] for tag, attrs in PageMarkup(result.content.decode()).elements if tag == "a" and attrs.get("rel") == "next"]
        self.assertEqual([parse_qs(urlsplit(link).query) for link in links], [{
            **{key: [value] for key, value in DAY.items()}, "workload_page": ["2"], "charges_page": ["2"],
        }])
        page = self.client.get(self.url + links[0])
        self.assertEqual((page.context["workload_page"].number, page.context["charges_page"].number), (2, 2))
