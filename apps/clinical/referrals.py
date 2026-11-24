"""Referral writes preserve the original patient-facing instruction."""
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.appointments.models import Appointment
from apps.common.permissions import require_permission

from .models import MedicalRecord, Referral
from .reception import _audit, lock_encounter_for_update


@transaction.atomic
def create_referral(*, actor, record_id, destination, reason):
    user = require_permission(actor, "consultation.access")
    snapshot = MedicalRecord.objects.get(pk=record_id)
    require_permission(user, "referral.create", snapshot)
    visit = lock_encounter_for_update(snapshot, actor_id=user.pk)
    user = require_permission(user, "referral.create", visit)
    if visit.appointment_id and visit.appointment.status != Appointment.Status.CHECKED_IN:
        raise ValidationError("Check in the linked appointment before recording a referral.")
    referral = Referral.objects.create(
        record=visit, referred_by_provider_id=user.pk, destination=destination.strip(), reason=reason.strip(),
    )
    _audit(user, "Referral recorded", referral)
    return referral


@transaction.atomic
def update_referral_status(*, actor, record_id, referral_id, status):
    user = require_permission(actor, "consultation.access")
    snapshot = MedicalRecord.objects.get(pk=record_id)
    require_permission(user, "referral.follow_up", snapshot)
    visit = lock_encounter_for_update(snapshot, actor_id=user.pk)
    user = require_permission(user, "referral.follow_up", visit)
    referral = visit.referrals.select_for_update().get(pk=referral_id)
    if status not in {Referral.Status.COMPLETED, Referral.Status.CANCELED}:
        raise ValidationError({"status": "Choose Completed or Canceled."})
    if referral.status != Referral.Status.PENDING:
        raise ValidationError("This referral already has a final follow-up status.")
    referral.status = status
    referral.save(update_fields=["status"])
    _audit(user, f"Referral marked {referral.get_status_display().lower()}", referral)
