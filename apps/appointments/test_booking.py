from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from threading import Barrier
from unittest import skipUnless

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.clinical.models import MedicalRecord
from apps.common.test_data import clinic_data
from apps.patients.models import Affiliation, Patient
from apps.providers.models import Provider
from apps.register.models import User

from .models import Appointment, ClinicRoom, Slot
from .services import book_appointment, cancel_appointment, reschedule_appointment


def second_patient():
    user = User.objects.create_user("BOOKING-OTHER", "booking-other@example.invalid")
    return Patient.objects.create(patient=user, affiliation=Affiliation.FACULTY)


def overlapping_slot(slot):
    user = User.objects.create_user("BOOKING-DENTIST", "booking-dentist@example.invalid", user_type=User.UserType.PROVIDER)
    dentist = Provider.objects.create(provider=user, provider_type=Provider.Type.DENTIST, is_active=True)
    room = ClinicRoom.objects.create(campus="Fictional", building="Booking", room_number="102")
    return Slot.objects.create(provider=dentist, room=room, start_time=slot.start_time + timedelta(minutes=5),
        end_time=slot.end_time + timedelta(minutes=5), is_active=True)


class BookingWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.provider, cls.slot, _ = clinic_data()
        cls.other = second_patient()
        cls.alternative = overlapping_slot(cls.slot)

    def setUp(self):
        self.client.force_login(self.patient.patient)

    def book(self, *, patient=None, slot=None):
        patient = patient or self.patient
        slot = slot or self.slot
        return book_appointment(actor=patient.patient, patient_id=patient.pk, slot_id=slot.pk,
            reason_for_visit="Fictional appointment reason")

    def payload(self, slot=None, **extra):
        slot = slot or self.slot
        return {"reason_for_visit": "Fictional appointment request", "expected_version": slot.version, **extra}

    def test_booking_confirmation_and_upcoming_are_own_account_scoped(self):
        url = reverse("booking:book", args=[self.slot.pk])
        self.assertContains(self.client.get(url), "Confirm appointment")
        self.assertFalse(Appointment.objects.exists())
        response = self.client.post(url, self.payload(patient_id=self.other.pk, status="Completed"), follow=True)
        self.assertContains(response, "Appointment booked.")
        appointment = Appointment.objects.get()
        self.assertEqual((appointment.patient_id, appointment.status), (self.patient.pk, Appointment.Status.SCHEDULED))
        self.assertContains(response, appointment.reason_for_visit)
        self.assertContains(self.client.get(reverse("booking:list")), reverse("booking:detail", args=[appointment.pk]))
        self.assertEqual(AuditLog.objects.get(target_table="appointment").actor_user_id, self.patient.pk)

    def test_browse_filters_manila_date_provider_and_type_and_hides_unbookable_slots(self):
        starts = datetime.combine(timezone.localdate() + timedelta(days=4), time(0, 10), timezone.get_default_timezone())
        slots = [
            Slot.objects.create(provider=self.provider, room=self.slot.room, start_time=starts,
                end_time=starts + timedelta(minutes=20), is_active=True),
            Slot.objects.create(provider=self.alternative.provider, room=self.alternative.room,
                start_time=starts, end_time=starts + timedelta(minutes=20), is_active=True),
        ]
        url = reverse("booking:browse")
        response = self.client.get(url, {"date": starts.date(), "provider": self.provider.pk, "provider_type": "Physician"})
        self.assertEqual([slot.pk for slot in response.context["page_obj"]], [slots[0].pk])
        self.assertContains(response, "12:10:00 AM")
        self.book(patient=self.other, slot=slots[0])
        ClinicRoom.objects.filter(pk=self.alternative.room_id).update(is_active=False)
        self.assertContains(self.client.get(url, {"date": starts.date()}), "No available times")
        self.assertNotContains(self.client.get(url), reverse("booking:book", args=[self.alternative.pk]))

    def test_history_contains_canceled_and_started_appointments(self):
        original = self.book()
        cancel_appointment(actor=self.patient.patient, appointment_id=original.pk)
        old = timezone.now() - timedelta(days=1)
        slot = Slot.objects.create(provider=self.provider, room=self.slot.room, start_time=old,
            end_time=old + timedelta(minutes=30), is_active=True)
        started = Appointment.objects.create(patient=self.patient, slot=slot, reason_for_visit="Fictional historical reason")
        current = self.book()
        listing = reverse("booking:list")
        self.assertEqual([item.pk for item in self.client.get(listing).context["page_obj"]], [current.pk])
        result = self.client.get(listing, {"view": "history"})
        self.assertEqual([item.pk for item in result.context["page_obj"]], [original.pk, started.pk])
        detail = self.client.get(reverse("booking:detail", args=[started.pk]))
        self.assertNotContains(detail, "Cancel appointment")

    def test_cross_patient_routes_and_mutations_are_denied(self):
        other_booking = self.book(patient=self.other)
        for route in ("detail", "cancel", "reschedule", "confirm_reschedule"):
            args = [other_booking.pk, self.alternative.pk] if route == "confirm_reschedule" else [other_booking.pk]
            with self.subTest(route=route):
                url = reverse(f"booking:{route}", args=args)
                self.assertEqual(self.client.get(url).status_code, 404)
                if route in ("cancel", "confirm_reschedule"):
                    self.assertEqual(self.client.post(url, self.payload(self.alternative)).status_code, 404)
        self.assertContains(self.client.get(reverse("booking:list")), "No upcoming appointments")
        other_booking.refresh_from_db()
        self.assertEqual(other_booking.status, Appointment.Status.SCHEDULED)

    def test_dual_role_uses_own_patient_profile_and_requires_one_to_access_pages(self):
        self.client.force_login(self.admin)
        listing = reverse("booking:list")
        self.assertEqual(self.client.get(listing).status_code, 404)
        Patient.objects.create(patient=self.admin, affiliation=Affiliation.STAFF)
        self.book(patient=self.other, slot=self.alternative)
        self.assertContains(self.client.get(listing), "No upcoming appointments")
        response = self.client.post(reverse("booking:book", args=[self.slot.pk]), self.payload())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Appointment.objects.filter(patient_id=self.admin.pk, slot=self.slot).exists())

    def test_stale_slot_and_conflicts_give_feedback_without_creating_duplicate_bookings(self):
        url = reverse("booking:book", args=[self.slot.pk])
        stale = self.payload()
        self.slot.start_time += timedelta(minutes=1)
        self.slot.save()
        self.assertContains(self.client.post(url, stale), "This slot changed.")
        self.assertFalse(Appointment.objects.exists())
        self.assertContains(self.client.post(url, self.payload(reason_for_visit=" ")), "This field is required.")
        self.book()
        other_time = reverse("booking:book", args=[self.alternative.pk])
        self.assertContains(self.client.post(other_time, self.payload(self.alternative)), "overlapping appointment")
        self.client.force_login(self.other.patient)
        response = self.client.post(url, self.payload(), follow=True)
        self.assertContains(response, "This slot is no longer open for booking.")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_cancellation_is_post_only_and_keeps_history(self):
        appointment = self.book()
        url = reverse("booking:cancel", args=[appointment.pk])
        self.assertContains(self.client.get(url), "Keep appointment")
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Appointment canceled.")
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CANCELED)
        self.assertIsNotNone(appointment.canceled_at)
        self.assertContains(self.client.post(url, follow=True), "Only future Scheduled appointments")
        self.assertEqual(AuditLog.objects.filter(action_performed="Appointment canceled").count(), 1)
        self.client.force_login(self.other.patient)
        self.assertContains(self.client.get(reverse("booking:browse")), reverse("booking:book", args=[self.slot.pk]))
        ClinicRoom.objects.filter(pk=self.slot.room_id).update(is_active=False)
        self.assertNotContains(self.client.get(reverse("booking:browse")), reverse("booking:book", args=[self.slot.pk]))

    def test_admin_on_behalf_cancellation_is_audited_even_with_unknown_legacy_reason(self):
        appointment = self.book()
        Appointment.objects.filter(pk=appointment.pk).update(reason_for_visit="")
        cancel_appointment(actor=self.admin, appointment_id=appointment.pk)
        appointment.refresh_from_db()
        self.assertEqual((appointment.status, appointment.reason_for_visit), (Appointment.Status.CANCELED, ""))
        self.assertTrue(AuditLog.objects.filter(actor_user=self.admin, target_record_id=appointment.pk,
            action_performed="Appointment canceled by Admin").exists())

    def test_rescheduling_can_use_a_time_overlapping_the_original_and_keeps_it_in_history(self):
        original = self.book()
        browse = reverse("booking:reschedule", args=[original.pk])
        url = reverse("booking:confirm_reschedule", args=[original.pk, self.alternative.pk])
        self.assertContains(self.client.get(browse), url)
        self.assertContains(self.client.get(url), original.reason_for_visit)
        self.assertEqual(Appointment.objects.count(), 1)
        response = self.client.post(url, self.payload(self.alternative), follow=True)
        self.assertContains(response, "Appointment rescheduled.")
        replacement = Appointment.objects.get(slot=self.alternative)
        original.refresh_from_db()
        self.assertEqual((original.status, replacement.status), (Appointment.Status.CANCELED, Appointment.Status.SCHEDULED))
        self.assertEqual(replacement.patient_id, self.patient.pk)
        self.assertEqual(AuditLog.objects.filter(target_table="appointment").count(), 3)

    def test_failed_transactional_replacement_leaves_the_original_scheduled(self):
        original = self.book()
        url = reverse("booking:confirm_reschedule", args=[original.pk, self.alternative.pk])
        response = self.client.post(url, self.payload(self.alternative, expected_version="stale"))
        self.assertContains(response, "This slot changed.")
        original.refresh_from_db()
        self.assertEqual(original.status, Appointment.Status.SCHEDULED)
        self.assertIsNone(original.canceled_at)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(target_table="appointment").count(), 1)
        with self.assertRaises(PermissionDenied):
            reschedule_appointment(actor=self.other.patient, appointment_id=original.pk,
                slot_id=self.alternative.pk, reason_for_visit="Forbidden")

    def test_linked_visit_cannot_be_canceled_or_rescheduled(self):
        appointment = self.book()
        MedicalRecord.objects.create(patient=self.patient, provider=self.provider, appointment=appointment,
            chief_complaint="Fictional linked visit")
        detail = self.client.get(reverse("booking:detail", args=[appointment.pk]))
        self.assertNotContains(detail, "Cancel appointment")
        for route, args in (("cancel", [appointment.pk]), ("confirm_reschedule", [appointment.pk, self.alternative.pk])):
            self.assertContains(self.client.post(reverse(f"booking:{route}", args=args), self.payload(self.alternative),
                follow=True), "Only future Scheduled appointments")
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)

    def test_csrf_is_required_for_all_booking_mutations(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.patient.patient)
        original = self.book()
        for route, args in (("book", [self.alternative.pk]), ("cancel", [original.pk]),
                            ("confirm_reschedule", [original.pk, self.alternative.pk])):
            with self.subTest(route=route):
                self.assertEqual(client.post(reverse(f"booking:{route}", args=args), self.payload(self.alternative)).status_code, 403)
        self.assertEqual(Appointment.objects.count(), 1)


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class BookingConcurrencyTests(TransactionTestCase):
    # Only the disposable test database flush cascades through archived FKs.
    available_apps = settings.INSTALLED_APPS

    def race(self, jobs):
        gate = Barrier(2, timeout=10)

        def request(job):
            patient, slot = job
            close_old_connections()
            try:
                gate.wait()
                book_appointment(actor=patient.patient, patient_id=patient.pk, slot_id=slot.pk,
                    reason_for_visit="Fictional simultaneous request")
                return "booked"
            except ValidationError as error:
                return str(error)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(request, jobs, timeout=20))
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(results.count("booked"), 1)
        return next(result for result in results if result != "booked")

    def test_different_patients_cannot_book_the_same_slot_simultaneously(self):
        _, patient, _, slot, _ = clinic_data()
        conflict = self.race([(patient, slot), (second_patient(), slot)])
        self.assertIn("already been booked", conflict)

    def test_same_patient_cannot_book_overlapping_slots_simultaneously(self):
        _, patient, _, slot, _ = clinic_data()
        conflict = self.race([(patient, slot), (patient, overlapping_slot(slot))])
        self.assertIn("overlapping appointment", conflict)
