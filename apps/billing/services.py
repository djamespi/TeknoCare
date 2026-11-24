"""Transactional tuition charge records and local simulated reconciliation."""
from uuid import UUID

from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from apps.audit.models import AuditLog
from apps.clinical.models import MedicalRecord
from apps.common.permissions import require_permission
from .models import AcademicTerm, StudentCharge


@transaction.atomic
def create_charge(*, record_id, term_id, description, amount, actor, request_code=None):
    actor = require_permission(actor, "billing.manage")
    record = MedicalRecord.objects.select_for_update().get(pk=record_id)
    term = AcademicTerm.objects.select_for_update().get(pk=term_id)
    actor = require_permission(actor, "billing.manage")
    description = description.strip()
    identity = {}
    if request_code is not None:
        try:
            request_code = UUID(str(request_code)).hex
        except ValueError as error:
            raise ValidationError("Reload the charge form and submit it again.") from error
        existing = StudentCharge.objects.filter(charge_code=request_code).first()
        if existing is not None:
            value = StudentCharge._meta.get_field("amount").to_python(amount)
            if (existing.created_by_user_id, existing.record_id, existing.term_id, existing.description, existing.amount) != (
                actor.pk, record.pk, term.pk, description, value,
            ):
                raise ValidationError("This form was already submitted with different details. Open a new charge form.")
            return existing
        identity["charge_code"] = request_code
    charge = StudentCharge.objects.create(record=record, term=term, description=description,
        amount=amount, created_by_user=actor, currency_code=settings.CLINIC_CURRENCY_CODE, **identity)
    AuditLog.objects.create(actor_user=actor, action_performed="Tuition charge created", target_table="student_charge", target_record_id=charge.pk)
    return charge


@transaction.atomic
def save_term(*, actor, academic_year, semester, start_date, end_date, is_open_for_charges, term_id=None):
    actor = require_permission(actor, "reference.manage")
    term = AcademicTerm.objects.select_for_update().get(pk=term_id) if term_id else AcademicTerm()
    identity = (academic_year.strip(), semester.strip(), start_date, end_date)
    if term_id and term.student_charges.exists() and identity != (term.academic_year, term.semester, term.start_date, term.end_date):
        raise ValidationError("Keep the identity/calendar of a charged term. Close it and create a new term instead.")
    term.academic_year, term.semester, term.start_date, term.end_date = identity
    term.is_open_for_charges = is_open_for_charges
    term.save()
    AuditLog.objects.create(actor_user=actor, action_performed="Academic term updated" if term_id else "Academic term created",
        target_table="academic_term", target_record_id=term.pk)
    return term


@transaction.atomic
def record_posting(*, charge_id, billing_reference, actor):
    return _post(*_lock_charge(actor, charge_id), billing_reference=billing_reference.strip())


def _lock_charge(actor, charge_id):
    actor = require_permission(actor, "billing.manage")
    snapshot = StudentCharge.objects.only("record_id", "term_id").get(pk=charge_id)
    record = MedicalRecord.objects.select_for_update().get(pk=snapshot.record_id)
    term = AcademicTerm.objects.select_for_update().get(pk=snapshot.term_id)
    charge = StudentCharge.objects.select_for_update().get(pk=charge_id)
    if (charge.record_id, charge.term_id) != (record.pk, term.pk):
        raise ValidationError("The charge changed. Reload and review it again.")
    charge.record, charge.term = record, term
    return require_permission(actor, "billing.manage"), charge


def _post(actor, charge, *, billing_reference, simulation=False):
    if charge.status == StudentCharge.Status.POSTED and charge.billing_reference == billing_reference:
        return charge
    if charge.status != StudentCharge.Status.PENDING:
        raise ValidationError("Only pending charges may be posted.")
    charge.status = StudentCharge.Status.POSTED
    charge.billing_reference = billing_reference
    charge.posted_at = timezone.now()
    charge.save()
    action = "Simulated tuition posting acknowledged" if simulation else "Tuition charge acknowledged"
    AuditLog.objects.create(actor_user=actor, action_performed=action, target_table="student_charge", target_record_id=charge.pk)
    return charge


@transaction.atomic
def void_charge(*, charge_id, reason, actor, reversal_reference=None):
    return _void(*_lock_charge(actor, charge_id), reason=reason.strip(),
        reversal_reference=reversal_reference.strip() if reversal_reference else None)


def _void(actor, charge, *, reason, reversal_reference, simulation=False):
    if charge.status == StudentCharge.Status.VOIDED:
        if (charge.void_reason, charge.reversal_reference) == (reason, reversal_reference):
            return charge
        raise ValidationError("Charge has already been voided.")
    if not reason:
        raise ValidationError({"reason": "Enter a reason for the void."})
    if charge.status == StudentCharge.Status.POSTED and not reversal_reference:
        raise ValidationError("Confirm a reversal before voiding a Posted charge.")
    if charge.status == StudentCharge.Status.PENDING and reversal_reference:
        raise ValidationError("A Pending charge has no posting to reverse.")
    charge.status = StudentCharge.Status.VOIDED
    charge.void_reason = reason
    charge.voided_at = timezone.now()
    charge.reversal_reference = reversal_reference
    charge.save()
    action = "Simulated tuition reversal confirmed" if simulation and reversal_reference else "Tuition charge voided"
    AuditLog.objects.create(actor_user=actor, action_performed=action, target_table="student_charge", target_record_id=charge.pk)
    return charge


@transaction.atomic
def simulate_posting(*, charge_id, actor, confirmed):
    if not confirmed:
        raise ValidationError("Confirm the simulated acknowledgment.")
    actor, charge = _lock_charge(actor, charge_id)
    return _post(actor, charge, billing_reference=f"DEMO-POST-{charge.charge_code}", simulation=True)


def is_simulated_posting(charge):
    return charge.billing_reference == f"DEMO-POST-{charge.charge_code}"


@transaction.atomic
def simulate_void(*, charge_id, actor, expected_status, reason, confirmed):
    if not confirmed:
        raise ValidationError("Confirm the void or simulated reversal.")
    actor, charge = _lock_charge(actor, charge_id)
    if expected_status not in {StudentCharge.Status.PENDING, StudentCharge.Status.POSTED}:
        raise ValidationError("Reload the charge before submitting a void.")
    if charge.status != expected_status and charge.status != StudentCharge.Status.VOIDED:
        raise ValidationError("Charge status changed. Reload and review the correct void action.")
    reversal_reference = None
    if expected_status == StudentCharge.Status.POSTED:
        if not is_simulated_posting(charge):
            raise ValidationError("Only a simulated posting can use the simulated reversal control.")
        reversal_reference = f"DEMO-REV-{charge.charge_code}"
    return _void(actor, charge, reason=reason.strip(), reversal_reference=reversal_reference, simulation=True)
