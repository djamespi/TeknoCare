"""Portal actions for the appointments feature."""
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.appointments.forms import BookingForm
from apps.appointments.models import Slot
from apps.appointments.services import book_appointment, cancel_appointment, save_slot
from apps.common.web import validated


def book(actor, data):
    values = validated(BookingForm({"reason_for_visit": data["reason"], "expected_version": data["version"]}))
    return book_appointment(actor=actor, patient_id=actor.pk, slot_id=data["slot_id"],
                            **values).pk


def cancel(actor, data):
    return cancel_appointment(actor=actor, appointment_id=data["id"]).pk


def add_slots(actor, data):
    start = timezone.make_aware(datetime.fromisoformat(f'{data["date"]}T{data["from"]}'))
    end = timezone.make_aware(datetime.fromisoformat(f'{data["date"]}T{data["to"]}'))
    minutes = data["minutes"]
    if type(minutes) is not int or not 5 <= minutes <= 180 or start >= end:
        raise ValidationError("Choose a valid time range and slot length.")
    duration = timedelta(minutes=minutes)
    count = 0
    while start + duration <= end:
        save_slot(actor=actor, provider_id=data["provider"], room_id=data["room"],
                  start_time=start, end_time=start + duration, is_active=True)
        start += duration
        count += 1
    if not count:
        raise ValidationError("The time range is shorter than one slot.")
    return count


def toggle_slot(actor, data):
    slot = Slot.objects.get(pk=data["id"])
    return save_slot(actor=actor, provider_id=slot.provider_id, room_id=slot.room_id,
                     start_time=slot.start_time, end_time=slot.end_time, is_active=not slot.is_active,
                     slot_id=slot.pk, expected_version=data["version"]).pk
