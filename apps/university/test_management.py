from datetime import date
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.appointments.models import ClinicRoom
from apps.appointments.services import book_appointment, save_room
from apps.audit.models import AuditLog
from apps.billing.models import AcademicTerm
from apps.billing.services import create_charge, record_posting, save_term, void_charge
from apps.common.test_data import clinic_data
from apps.patients.models import Patient
from apps.register.models import User
from .models import Department
from .services import save_department


class ManagementPageTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()
        self.pages = [reverse(name) for name in (
            "university:management", "university:department_list", "university:department_create",
            "appointments:room_list", "appointments:room_create", "billing:term_list", "billing:term_create",
            "providers:provider_list", "providers:provider_create", "providers:provider_attach",
            "accounts:personnel_list", "accounts:personnel_create")]
        self.pages += [reverse("appointments:room_edit", args=[self.slot.room_id]),
            reverse("providers:provider_edit", args=[self.provider.pk]), reverse("accounts:status", args=[self.patient.pk])]

    def test_every_management_page_requires_admin_on_get_and_post(self):
        for url in self.pages:
            self.assertEqual(self.client.get(url).status_code, 302)
        for user in (self.patient.patient, self.provider.provider):
            self.client.force_login(user)
            for url in self.pages:
                with self.subTest(user=user.user_type, url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)
                    self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.assertFalse(AuditLog.objects.exists())

    def test_admin_pages_use_shared_dark_layout_and_get_does_not_write(self):
        from apps.user_settings.models import UserSettings
        UserSettings.objects.create(user=self.admin, dark_mode=True)
        self.client.force_login(self.admin)
        original_counts = (User.objects.count(), Department.objects.count(), ClinicRoom.objects.count(), AuditLog.objects.count())
        for url in self.pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "base.html")
                self.assertContains(response, 'data-theme="dark"')
                self.assertNotContains(response, self.record.chief_complaint)
        self.assertEqual(original_counts, (User.objects.count(), Department.objects.count(), ClinicRoom.objects.count(), AuditLog.objects.count()))

    def test_forms_require_csrf_and_no_delete_or_list_post_is_supported(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        for name in ("university:department_create", "appointments:room_create", "billing:term_create", "providers:provider_create", "providers:provider_attach", "accounts:personnel_create"):
            self.assertEqual(client.post(reverse(name), {}).status_code, 403)
        self.client.force_login(self.admin)
        for name in ("university:department_list", "appointments:room_list", "billing:term_list", "providers:provider_list", "accounts:personnel_list"):
            self.assertEqual(self.client.post(reverse(name), {}).status_code, 405)
        self.assertEqual(self.client.delete(reverse("appointments:room_edit", args=[self.slot.room_id])).status_code, 405)
        self.assertEqual(self.client.get(reverse("appointments:room_edit", args=[999999])).status_code, 404)
        self.assertEqual(self.client.get("/clinic/rooms/1/delete/").status_code, 404)

    def test_admin_can_create_reference_rows_without_charges_or_id_injection(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("university:department_create"), {"code": " TEST ", "name": "Fictional Department", "is_active": "on", "department_id": 888}, follow=True)
        self.assertContains(response, "Department saved")
        self.assertNotEqual(Department.objects.get(code="TEST").pk, 888)
        response = self.client.post(reverse("appointments:room_create"), {"campus": "Fictional", "building": "Demo", "room_number": "002", "is_active": "on"})
        self.assertRedirects(response, reverse("appointments:room_list"))
        response = self.client.post(reverse("billing:term_create"), {"academic_year": "2026-2027", "semester": "Fictional", "start_date": "2026-08-01", "end_date": "2026-12-31", "is_open_for_charges": "on"})
        self.assertRedirects(response, reverse("billing:term_list"))
        term = AcademicTerm.objects.get(semester="Fictional")
        self.assertTrue(term.is_open_for_charges)
        self.assertEqual(term.student_charges.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 3)

    def test_duplicate_and_invalid_reference_forms_show_errors_without_partial_writes(self):
        Department.objects.create(code="TAKEN", name="Fictional")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("university:department_create"), {"code": "TAKEN", "name": "Duplicate"})
        self.assertContains(response, "Please check your details")
        self.assertEqual(Department.objects.count(), 1)
        response = self.client.post(reverse("billing:term_create"), {"academic_year": "2026-2028", "semester": "Test", "start_date": "2026-12-31", "end_date": "2026-08-01"})
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(AcademicTerm.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_search_status_and_pagination_work_with_escaped_content(self):
        for index in range(12):
            Department.objects.create(code=f"DEMO-{index:02}", name="Fictional <script>unsafe</script>", is_active=index != 11)
        self.client.force_login(self.admin)
        url = reverse("university:department_list")
        response = self.client.get(url, {"q": "DEMO", "state": "active"})
        self.assertEqual(len(response.context["page_obj"]), 10)
        self.assertNotContains(response, "<script>unsafe</script>")
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, "state=active&amp;page=2")
        response = self.client.get(url, {"q": "DEMO", "state": "active", "page": "9999"})
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"]), 1)
        response = self.client.get(url, {"state": "inactive", "page": "not-a-number"})
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertContains(response, "DEMO-11")
        response = self.client.get(url, {"q": "absent"})
        self.assertContains(response, "No matching entries")
        response = self.client.get(url, {"state": "invented"})
        self.assertContains(response, "Please check your details")
        self.assertEqual(len(response.context["page_obj"]), 0)


class ReferenceLifecycleTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()

    def room_values(self, **overrides):
        values = dict(actor=self.admin, room_id=self.slot.room_id, campus=self.slot.room.campus,
            building=self.slot.room.building, room_number=self.slot.room.room_number, is_active=False)
        values.update(overrides)
        return values

    def test_service_boundary_rejects_wrong_role_and_stale_admin(self):
        operations = [lambda actor: save_department(actor=actor, code="X", name="X", is_active=True),
            lambda actor: save_room(actor=actor, campus="X", building="X", room_number="X", is_active=True),
            lambda actor: save_term(actor=actor, academic_year="2026-2027", semester="X", start_date=date(2026, 1, 1), end_date=date(2026, 2, 1), is_open_for_charges=False)]
        User.objects.filter(pk=self.admin.pk).update(account_status="Suspended")
        for operation in operations:
            for actor in (self.admin, self.patient.patient, self.provider.provider, None):
                with self.assertRaises(PermissionDenied):
                    operation(actor)

    def test_department_deactivation_keeps_patient_and_protects_referenced_code(self):
        department = save_department(actor=self.admin, code="FAC", name="Fictional", is_active=True)
        self.patient.department = department
        self.patient.save()
        with self.assertRaises(ValidationError):
            save_department(actor=self.admin, department_id=department.pk, code="DIFFERENT", name="New", is_active=True)
        save_department(actor=self.admin, department_id=department.pk, code="FAC", name="Fictional", is_active=False)
        self.patient.refresh_from_db()
        self.assertEqual((self.patient.department_id, self.patient.affiliation), (department.pk, "Student"))

    def test_room_deactivation_disables_future_slots_without_deleting_history(self):
        save_room(**self.room_values())
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.is_active)
        self.assertTrue(self.provider.medical_records.filter(pk=self.record.pk).exists())
        with self.assertRaises(ValidationError):
            book_appointment(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="No longer available", actor=self.admin)
        save_room(**self.room_values(is_active=True))
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.is_active)

    def test_live_booking_blocks_room_deactivation_and_location_rewrite(self):
        appointment = book_appointment(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="Fictional", actor=self.admin)
        with self.assertRaises(ValidationError):
            save_room(**self.room_values())
        with self.assertRaises(ValidationError):
            save_room(**self.room_values(room_number="REWRITTEN", is_active=True))
        appointment.refresh_from_db()
        self.slot.refresh_from_db()
        self.assertEqual(appointment.status, "Scheduled")
        self.assertTrue(self.slot.is_active)
        self.assertTrue(ClinicRoom.objects.get(pk=self.slot.room_id).is_active)

    def test_charged_term_closes_without_mutating_lines_and_allows_reversal(self):
        values = dict(actor=self.admin, academic_year="2026-2027", semester="First", start_date=date(2026, 8, 1), end_date=date(2026, 12, 31), is_open_for_charges=True)
        term = save_term(**values)
        charge = create_charge(record_id=self.record.pk, term_id=term.pk, description="Fictional", amount="100.00", actor=self.admin)
        record_posting(charge_id=charge.pk, billing_reference="TEST-REF", actor=self.admin)
        with self.assertRaises(ValidationError):
            save_term(**dict(values, term_id=term.pk, semester="Rewritten"))
        save_term(**dict(values, term_id=term.pk, is_open_for_charges=False))
        charge.refresh_from_db()
        self.assertEqual(charge.status, "Posted")
        result = void_charge(charge_id=charge.pk, actor=self.admin, reason="Fictional reversal", reversal_reference="TEST-REV")
        self.assertEqual(result.billing_reference, "TEST-REF")
        self.assertEqual(result.status, "Voided")

    def test_audit_failure_rolls_back_reference_and_slot_changes(self):
        with patch("apps.appointments.services.AuditLog.objects.create", side_effect=ValidationError("Audit unavailable")):
            with self.assertRaises(ValidationError):
                save_room(**self.room_values())
        self.slot.refresh_from_db()
        self.assertTrue(self.slot.is_active)
        self.assertTrue(ClinicRoom.objects.get(pk=self.slot.room_id).is_active)
