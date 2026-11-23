"""Transactional writes for the appointment feature; no HTTP concerns here."""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.patients.models import Patient
from apps.common.permissions import require_permission
from apps.audit.models import AuditLog
from apps.providers.eligibility import provider_is_eligible
from apps.providers.models import Provider
from apps.register.models import User
from .models import Appointment, ClinicRoom, Slot, protected_slot_appointments


def _lock_slot_resources(provider_ids, room_ids, *, other_account_ids=()):
    # Match the order used for availability and clinic resource deactivation.
    account_ids = provider_ids.union(other_account_ids)
    list(User.objects.select_for_update(no_key=True).filter(pk__in=account_ids).order_by("pk").values_list("pk", flat=True))
    providers = Provider.objects.select_for_update().filter(pk__in=provider_ids).order_by("pk").in_bulk()
    rooms = ClinicRoom.objects.select_for_update().filter(pk__in=room_ids).order_by("pk").in_bulk()
    return providers, rooms


def _lock_booking_slots(*slot_ids, account_ids):
    snapshots = Slot.objects.in_bulk(slot_ids)
    if len(snapshots) != len(set(slot_ids)):
        raise ValidationError("Availability changed. Choose another time.")
    providers, rooms = _lock_slot_resources(
        {slot.provider_id for slot in snapshots.values()},
        {slot.room_id for slot in snapshots.values() if slot.room_id is not None},
        other_account_ids=account_ids,
    )
    locked = Slot.objects.select_for_update().filter(pk__in=snapshots).order_by("pk").in_bulk()
    if len(locked) != len(snapshots):
        raise ValidationError("Availability changed. Choose another time.")
    for slot in locked.values():
        if slot.schedule != snapshots[slot.pk].schedule:
            raise ValidationError("Availability changed. Choose the time again.")
        slot.provider = providers[slot.provider_id]
        slot.room = rooms.get(slot.room_id)
    return locked


def _create_booking(*, actor, patient, slot, reason_for_visit, expected_version):
    if not User.objects.filter(pk=patient.pk, account_status=User.AccountStatus.ACTIVE).exists():
        raise ValidationError("Booking requires an active patient account.")
    if expected_version is not None and slot.version != expected_version:
        raise ValidationError("This slot changed. Review the current details before booking.")
    if not slot.is_active or not slot.room or not slot.room.is_active or not provider_is_eligible(slot.provider_id):
        raise ValidationError("This slot is no longer open for booking. Choose another time.")
    if slot.start_time <= timezone.now():
        raise ValidationError("This slot has already started. Choose another time.")
    if protected_slot_appointments(slot.appointments).exists():
        raise ValidationError("This slot has already been booked. Choose another time.")
    reason = reason_for_visit.strip()
    if not reason:
        raise ValidationError({"reason_for_visit": "Enter a reason for the visit."})
    appointment = Appointment.objects.create(patient=patient, slot=slot, reason_for_visit=reason)
    AuditLog.objects.create(actor_user=actor, action_performed="Appointment booked", target_table="appointment", target_record_id=appointment.pk)
    return appointment


@transaction.atomic
def book_appointment(*, patient_id, slot_id, reason_for_visit, actor, expected_version=None):
    patient = Patient.objects.select_for_update().get(pk=patient_id)
    actor = require_permission(actor, "appointment.book", patient)
    slot = _lock_booking_slots(slot_id, account_ids=(patient.pk, actor.pk))[slot_id]
    actor = require_permission(actor, "appointment.book", patient)
    return _create_booking(actor=actor, patient=patient, slot=slot, reason_for_visit=reason_for_visit,
        expected_version=expected_version)


@transaction.atomic
def save_slot(*, actor, provider_id, room_id, start_time, end_time, is_active, slot_id=None, expected_version=None):
    actor = require_permission(actor, "schedule.access")
    if timezone.is_naive(start_time) or timezone.is_naive(end_time):
        raise ValidationError("Use timezone-aware start and end times.")
    snapshot = Slot.objects.get(pk=slot_id) if slot_id is not None else None
    provider_ids = {provider_id}
    room_ids = {room_id} if room_id is not None else set()
    if snapshot:
        provider_ids.add(snapshot.provider_id)
        if snapshot.room_id is not None:
            room_ids.add(snapshot.room_id)

    # Match booking and resource deactivation: provider accounts, providers,
    # rooms, then the slot. Order multiple rows of each kind by primary key.
    providers, rooms = _lock_slot_resources(provider_ids, room_ids, other_account_ids=(actor.pk,))
    provider = providers.get(provider_id)
    if provider is None:
        raise ValidationError({"provider": "Choose an existing provider."})
    require_permission(actor, "schedule.manage", provider)

    slot = Slot()
    if snapshot:
        slot = Slot.objects.select_for_update().get(pk=snapshot.pk)
        if slot.schedule != snapshot.schedule or (expected_version is not None and slot.version != expected_version):
            raise ValidationError("This slot changed. Open it again before saving.")
        require_permission(actor, "schedule.manage", providers[slot.provider_id])
        if slot.start_time <= timezone.now():
            raise ValidationError("Availability that already started is read-only.")
        if protected_slot_appointments(slot.appointments).exists():
            raise ValidationError("A booking or linked visit protects this slot from availability changes.")

    if start_time <= timezone.now():
        raise ValidationError({"start_time": "Start time must be in the future."})
    schedule_changed = (provider_id, room_id, start_time, end_time) != slot.schedule
    room = rooms.get(room_id)
    if is_active or schedule_changed:
        if not provider_is_eligible(provider.pk):
            raise ValidationError({"provider": "Choose an active provider with a reviewed designation and an Active account."})
        if not room or not room.is_active:
            raise ValidationError({"room": "Choose an active clinic room."})

    if not schedule_changed and is_active == slot.is_active:
        return slot
    slot.provider = provider
    slot.room = room
    slot.start_time, slot.end_time = start_time, end_time
    slot.is_active = is_active
    slot.save()
    AuditLog.objects.create(actor_user=actor, action_performed="Availability updated" if snapshot else "Availability created",
        target_table="slot", target_record_id=slot.pk)
    return slot


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
    snapshot = Appointment.objects.get(pk=appointment_id)
    actor = require_permission(actor, "appointment.cancel", snapshot)
    Patient.objects.select_for_update().get(pk=snapshot.patient_id)
    slot = _lock_booking_slots(snapshot.slot_id, account_ids=(snapshot.patient_id, actor.pk,))[snapshot.slot_id]
    appointment = _lock_appointment(snapshot, slot)
    _cancel_locked_appointment(actor, appointment)
    return appointment


def _lock_appointment(snapshot, slot):
    appointment = Appointment.objects.select_for_update().get(pk=snapshot.pk)
    if appointment.patient_id != snapshot.patient_id or appointment.slot_id != slot.pk:
        raise ValidationError("This appointment changed. Open it again.")
    appointment.slot = slot
    return appointment


def _cancel_locked_appointment(actor, appointment):
    actor = require_permission(actor, "appointment.cancel", appointment)
    appointment.status = Appointment.Status.CANCELED
    appointment.canceled_at = timezone.now()
    # Only the guarded transition is written, including when a legacy reason is unknown.
    Appointment.objects.filter(pk=appointment.pk).update(status=appointment.status, canceled_at=appointment.canceled_at)
    action = "Appointment canceled" if actor.pk == appointment.patient_id else "Appointment canceled by Admin"
    AuditLog.objects.create(actor_user=actor, action_performed=action, target_table="appointment", target_record_id=appointment.pk)


@transaction.atomic
def reschedule_appointment(*, appointment_id, slot_id, reason_for_visit, actor, expected_version=None):
    snapshot = Appointment.objects.get(pk=appointment_id)
    patient = Patient.objects.select_for_update().get(pk=snapshot.patient_id)
    actor = require_permission(actor, "appointment.book", patient)
    if snapshot.slot_id == slot_id:
        raise ValidationError("Choose a different time for this appointment.")
    slots = _lock_booking_slots(snapshot.slot_id, slot_id, account_ids=(patient.pk, actor.pk))
    appointment = _lock_appointment(snapshot, slots[snapshot.slot_id])
    _cancel_locked_appointment(actor, appointment)
    return _create_booking(actor=actor, patient=patient, slot=slots[slot_id], reason_for_visit=reason_for_visit,
        expected_version=expected_version)
