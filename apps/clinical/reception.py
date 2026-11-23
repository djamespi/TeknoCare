"""Operational transitions for reception and encounter intake."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.appointments.services import lock_appointment_for_update
from apps.audit.models import AuditLog
from apps.common.permissions import require_permission
from apps.patients.models import Patient
from apps.providers.eligibility import provider_is_eligible
from apps.providers.models import Provider
from apps.register.models import User

from .models import MedicalRecord


def _audit(actor, action, target):
    AuditLog.objects.create(actor_user=actor, action_performed=action,
        target_table=target._meta.db_table, target_record_id=target.pk)


def can_check_in(appointment, now):
    return (
        appointment.status == Appointment.Status.SCHEDULED
        and appointment.slot.end_time > now
        and timezone.localtime(appointment.slot.start_time).date() <= timezone.localdate(now)
    )


def can_mark_no_show(appointment, now):
    return appointment.status == Appointment.Status.SCHEDULED and appointment.slot.end_time <= now


@transaction.atomic
def change_appointment_status(*, actor, appointment_id, action):
    actor = require_permission(actor, "reception.access")
    snapshot = Appointment.objects.get(pk=appointment_id)
    appointment = lock_appointment_for_update(snapshot, actor_id=actor.pk)
    actor = require_permission(actor, "reception.appointment", appointment)
    now = timezone.now()
    if action == "check_in":
        if not can_check_in(appointment, now):
            raise ValidationError("Check-in requires a Scheduled appointment on this clinic day, before the slot ends.")
        if not appointment.patient.patient.is_active:
            raise ValidationError("Check-in requires an active patient account.")
        status, event = Appointment.Status.CHECKED_IN, "Appointment checked in"
    elif action == "no_show":
        if not can_mark_no_show(appointment, now):
            raise ValidationError("A Scheduled appointment can be marked No show only after its slot ends.")
        if MedicalRecord.objects.filter(appointment=appointment).exists():
            raise ValidationError("A linked encounter protects this appointment.")
        status, event = Appointment.Status.NO_SHOW, "Appointment marked no show"
    elif action == "complete":
        if appointment.status != Appointment.Status.CHECKED_IN or not MedicalRecord.objects.filter(
            appointment=appointment, status=MedicalRecord.Status.FINALIZED,
        ).exists():
            raise ValidationError("Completion requires a Checked in appointment and a finalized encounter.")
        status, event = Appointment.Status.COMPLETED, "Appointment completed"
    else:
        raise ValidationError("Choose a valid reception action.")
    # The guarded transition preserves any missing legacy appointment reason.
    Appointment.objects.filter(pk=appointment.pk).update(status=status)
    appointment.status = status
    _audit(actor, event, appointment)
    return appointment


def _check_attending(provider_id):
    if not provider_is_eligible(provider_id):
        raise ValidationError({"provider": "Choose an active provider with a reviewed designation."})


def _open_draft(actor, patient, provider_id, appointment=None):
    _check_attending(provider_id)
    if not patient.patient.is_active:
        raise ValidationError("Opening an encounter requires an active patient account.")
    if provider_id == patient.pk:
        raise ValidationError({"provider": "Choose a different attending provider for this patient."})
    visit = MedicalRecord.objects.create(patient=patient, provider_id=provider_id, appointment=appointment)
    _audit(actor, "Scheduled encounter opened" if appointment else "Walk-in encounter opened", visit)
    return visit


@transaction.atomic
def open_scheduled_encounter(*, actor, appointment_id, provider_id):
    actor = require_permission(actor, "reception.access")
    snapshot = Appointment.objects.get(pk=appointment_id)
    appointment = lock_appointment_for_update(snapshot, actor_id=actor.pk, attending_provider_ids=(provider_id,))
    actor = require_permission(actor, "reception.appointment", appointment)
    if provider_id != appointment.slot.provider_id:
        require_permission(actor, "reception.assign")
    if appointment.status != Appointment.Status.CHECKED_IN:
        raise ValidationError("Check in the patient before opening an encounter.")
    if MedicalRecord.objects.filter(appointment=appointment).exists():
        raise ValidationError("An encounter is already linked to this appointment.")
    return _open_draft(actor, appointment.patient, provider_id, appointment)


def _lock_intake_providers(actor_id, patient_id, provider_ids):
    accounts = set(provider_ids) | {actor_id, patient_id}
    list(User.objects.select_for_update(no_key=True).filter(pk__in=accounts).order_by("pk").values_list("pk", flat=True))
    list(Provider.objects.select_for_update().filter(pk__in=provider_ids).order_by("pk").values_list("pk", flat=True))


@transaction.atomic
def open_walkin_encounter(*, actor, patient_id, provider_id):
    actor = require_permission(actor, "reception.walkin")
    patient = Patient.objects.select_for_update().get(pk=patient_id)
    _lock_intake_providers(actor.pk, patient.pk, (provider_id,))
    actor = require_permission(actor, "reception.walkin")
    if patient.medical_records.filter(appointment__isnull=True, status=MedicalRecord.Status.DRAFT).exists():
        raise ValidationError("This patient already has an open walk-in encounter.")
    return _open_draft(actor, patient, provider_id)


@transaction.atomic
def assign_encounter(*, actor, record_id, provider_id, expected_provider_id):
    actor = require_permission(actor, "reception.assign")
    snapshot = MedicalRecord.objects.get(pk=record_id)
    providers = (snapshot.provider_id, provider_id)
    if snapshot.appointment_id is None:
        Patient.objects.select_for_update().get(pk=snapshot.patient_id)
        _lock_intake_providers(actor.pk, snapshot.patient_id, providers)
    else:
        appointment = lock_appointment_for_update(snapshot.appointment, actor_id=actor.pk, attending_provider_ids=providers)
        if appointment.status != Appointment.Status.CHECKED_IN:
            raise ValidationError("An attended appointment is required to change the attending provider.")
    visit = MedicalRecord.objects.select_for_update().get(pk=record_id)
    actor = require_permission(actor, "reception.assign")
    require_permission(actor, "reception.record", visit)
    if visit.status != MedicalRecord.Status.DRAFT:
        raise ValidationError("Only Draft encounters can be reassigned.")
    if (visit.provider_id != expected_provider_id or visit.provider_id != snapshot.provider_id
        or visit.patient_id != snapshot.patient_id or visit.appointment_id != snapshot.appointment_id):
        raise ValidationError("This encounter changed. Review it again before assigning.")
    _check_attending(provider_id)
    if provider_id == visit.patient_id:
        raise ValidationError({"provider": "Choose a different attending provider for this patient."})
    if provider_id != visit.provider_id:
        visit.provider_id = provider_id
        visit.save(update_fields=["provider"])
        _audit(actor, "Attending provider reassigned", visit)
    return visit
