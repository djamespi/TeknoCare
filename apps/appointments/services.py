"""Transactional writes for the appointment feature; no HTTP concerns here."""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.patients.models import Patient
from apps.common.permissions import require_permission
from apps.audit.models import AuditLog
from .models import Appointment, Slot


@transaction.atomic
def book_appointment(*, patient_id, slot_id, reason_for_visit, actor):
    patient = Patient.objects.select_for_update().get(pk=patient_id)
    actor = require_permission(actor, "appointment.book", patient)
    slot = Slot.objects.select_for_update().select_related("provider", "room").get(pk=slot_id)
    if not patient.patient.is_active or not slot.provider.provider.is_active:
        raise ValidationError("Booking requires active patient and provider accounts.")
    if not slot.is_active or not slot.provider.is_active or slot.provider.provider_type not in {"Physician", "Dentist", "Nurse"} or not slot.room or not slot.room.is_active:
        raise ValidationError("Booking requires an active, verified provider, room and slot.")
    if slot.start_time <= timezone.now():
        raise ValidationError("Choose a future slot.")
    appointment = Appointment.objects.create(patient=patient, slot=slot, reason_for_visit=reason_for_visit)
    AuditLog.objects.create(actor_user=actor, action_performed="Appointment booked", target_table="appointment", target_record_id=appointment.pk)
    return appointment


@transaction.atomic
def cancel_appointment(*, appointment_id, actor):
    appointment = Appointment.objects.select_for_update().get(pk=appointment_id)
    actor = require_permission(actor, "appointment.cancel", appointment)
    appointment.status = Appointment.Status.CANCELED
    appointment.canceled_at = timezone.now()
    appointment.save()
    AuditLog.objects.create(actor_user=actor, action_performed="Appointment canceled", target_table="appointment", target_record_id=appointment.pk)
    return appointment
