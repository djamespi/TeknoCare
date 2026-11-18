"""Transactional writes for the appointment feature; no HTTP concerns here."""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.patients.models import Patient
from apps.common.permissions import require_permission
from apps.audit.models import AuditLog
from .models import Appointment, ClinicRoom, Slot


@transaction.atomic
def book_appointment(*, patient_id, slot_id, reason_for_visit, actor):
    patient = Patient.objects.select_for_update().get(pk=patient_id)
    actor = require_permission(actor, "appointment.book", patient)
    from apps.providers.models import Provider
    from apps.register.models import User
    snapshot = Slot.objects.get(pk=slot_id)
    provider_user = User.objects.select_for_update().get(pk=snapshot.provider_id)
    provider = Provider.objects.select_for_update().get(pk=snapshot.provider_id)
    room = ClinicRoom.objects.select_for_update().filter(pk=snapshot.room_id).first()
    slot = Slot.objects.select_for_update().get(pk=slot_id)
    if slot.provider_id != snapshot.provider_id or slot.room_id != snapshot.room_id:
        raise ValidationError("Availability changed. Select the slot again.")
    provider.provider = provider_user
    slot.provider, slot.room = provider, room
    if not patient.patient.is_active or not slot.provider.provider.is_active or provider_user.user_type not in {"Admin", "Provider"}:
        raise ValidationError("Booking requires active patient and provider accounts.")
    if not slot.is_active or not slot.provider.is_active or slot.provider.provider_type not in {"Physician", "Dentist", "Nurse"} or not slot.room or not slot.room.is_active:
        raise ValidationError("Booking requires an active, verified provider, room and slot.")
    if slot.start_time <= timezone.now():
        raise ValidationError("Choose a future slot.")
    appointment = Appointment.objects.create(patient=patient, slot=slot, reason_for_visit=reason_for_visit)
    AuditLog.objects.create(actor_user=actor, action_performed="Appointment booked", target_table="appointment", target_record_id=appointment.pk)
    return appointment


@transaction.atomic
def save_room(*, actor, campus, building, room_number, is_active, room_id=None):
    actor = require_permission(actor, "reference.manage")
    room = ClinicRoom.objects.select_for_update().get(pk=room_id) if room_id else ClinicRoom()
    location = (campus.strip(), building.strip(), room_number.strip())
    if room_id:
        slots = room.slots.select_for_update().order_by("pk")
        slot_ids = list(slots.values_list("pk", flat=True))
        if location != (room.campus, room.building, room.room_number) and slot_ids:
            raise ValidationError("Create a new room to preserve the location of existing availability and visits.")
        if not is_active:
            if Appointment.objects.filter(slot_id__in=slot_ids, status__in=["Scheduled", "Checked-In"]).exists():
                raise ValidationError("Resolve scheduled/checked-in bookings before deactivating this room. No bookings were canceled.")
            Slot.objects.filter(pk__in=slot_ids, end_time__gt=timezone.now(), is_active=True).update(is_active=False)
    room.campus, room.building, room.room_number = location
    room.is_active = is_active
    room.save()
    AuditLog.objects.create(actor_user=actor, action_performed="Clinic room updated" if room_id else "Clinic room created",
        target_table="clinic_room", target_record_id=room.pk)
    return room


@transaction.atomic
def cancel_appointment(*, appointment_id, actor):
    appointment = Appointment.objects.select_for_update().get(pk=appointment_id)
    actor = require_permission(actor, "appointment.cancel", appointment)
    appointment.status = Appointment.Status.CANCELED
    appointment.canceled_at = timezone.now()
    appointment.save()
    AuditLog.objects.create(actor_user=actor, action_performed="Appointment canceled", target_table="appointment", target_record_id=appointment.pk)
    return appointment
