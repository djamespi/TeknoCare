"""Transactional writes for the appointment feature; no HTTP concerns here."""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.patients.models import Patient
from .models import Appointment, Slot


@transaction.atomic
def book_appointment(*, patient_id, slot_id, reason_for_visit):
    # Same patient lock serializes bookings across different slots.
    patient = Patient.objects.select_for_update().get(pk=patient_id)
    slot = Slot.objects.select_for_update().select_related("provider", "room").get(pk=slot_id)
    if not patient.patient.is_active or not slot.provider.provider.is_active:
        raise ValidationError("Booking requires active patient and provider accounts.")
    if slot.start_time <= timezone.now():
        raise ValidationError("Choose a future slot.")
    return Appointment.objects.create(patient=patient, slot=slot, reason_for_visit=reason_for_visit)


@transaction.atomic
def cancel_appointment(*, appointment_id):
    appointment = Appointment.objects.select_for_update().get(pk=appointment_id)
    appointment.status = Appointment.Status.CANCELED
    appointment.canceled_at = timezone.now()
    appointment.save()
    return appointment
