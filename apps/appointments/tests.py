from datetime import timedelta
from unittest import skipUnless
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from apps.common.test_data import clinic_data
from .models import Appointment, Slot
from .services import book_appointment, cancel_appointment


class AppointmentModelTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()

    def test_cancel_frees_slot_and_preserves_history(self):
        first = book_appointment(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="First visit")
        cancel_appointment(appointment_id=first.pk)
        second = book_appointment(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="Replacement")
        self.assertEqual(self.slot.appointments.count(), 2)
        self.assertNotEqual(first.pk, second.pk)
        self.assertTrue(self.slot.is_booked)
        self.assertEqual(second.provider, self.provider)

    def test_database_rejects_bulk_double_booking(self):
        book_appointment(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="First")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.bulk_create([Appointment(patient=self.patient, slot=self.slot, reason_for_visit="Duplicate")])

    def test_overlapping_provider_availability_rejected(self):
        with self.assertRaises(ValidationError):
            Slot.objects.create(provider=self.provider, room=self.slot.room, start_time=self.slot.start_time + timedelta(minutes=1),
                end_time=self.slot.end_time, is_active=True)

    def test_occupied_slot_cannot_be_rescheduled(self):
        book_appointment(patient_id=self.patient.pk, slot_id=self.slot.pk, reason_for_visit="Visit")
        self.slot.start_time += timedelta(minutes=1)
        with self.assertRaises(ValidationError):
            self.slot.save()

    @skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL range exclusion constraints")
    def test_postgres_blocks_bulk_overlapping_active_slots(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Slot.objects.bulk_create([Slot(provider=self.provider, room=self.slot.room,
                start_time=self.slot.start_time + timedelta(minutes=1), end_time=self.slot.end_time, is_active=True)])
