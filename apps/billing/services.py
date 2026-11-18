"""Record verified finance acknowledgments; these functions never call a gateway."""
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from apps.common.permissions import require_permission
from .models import AcademicTerm, StudentCharge


@transaction.atomic
def create_charge(*, record_id, term_id, description, amount, actor):
    actor = require_permission(actor, "billing.manage")
    from apps.clinical.models import MedicalRecord
    record = MedicalRecord.objects.select_for_update().get(pk=record_id)
    term = AcademicTerm.objects.select_for_update().get(pk=term_id)
    charge = StudentCharge.objects.create(record=record, term=term, description=description,
        amount=amount, created_by_user=actor, currency_code=settings.CLINIC_CURRENCY_CODE)
    from apps.audit.models import AuditLog
    AuditLog.objects.create(actor_user=actor, action_performed="Tuition charge created", target_table="student_charge", target_record_id=charge.pk)
    return charge


@transaction.atomic
def record_posting(*, charge_id, billing_reference, actor):
    actor = require_permission(actor, "billing.manage")
    charge = StudentCharge.objects.select_for_update().select_related("record").get(pk=charge_id)
    AcademicTerm.objects.select_for_update().get(pk=charge.term_id)
    if charge.status == StudentCharge.Status.POSTED and charge.billing_reference == billing_reference:
        return charge  # Retrying an acknowledgment does not create another line.
    if charge.status != StudentCharge.Status.PENDING:
        raise ValidationError("Only pending charges may be posted.")
    charge.status = StudentCharge.Status.POSTED
    charge.billing_reference = billing_reference.strip()
    charge.posted_at = timezone.now()
    charge.save()
    from apps.audit.models import AuditLog
    AuditLog.objects.create(actor_user=actor, action_performed="Tuition charge acknowledged", target_table="student_charge", target_record_id=charge.pk)
    return charge


@transaction.atomic
def void_charge(*, charge_id, reason, actor, reversal_reference=None):
    actor = require_permission(actor, "billing.manage")
    charge = StudentCharge.objects.select_for_update().get(pk=charge_id)
    if charge.status == StudentCharge.Status.VOIDED:
        raise ValidationError("Charge has already been voided.")
    charge.status = StudentCharge.Status.VOIDED
    charge.void_reason = reason.strip()
    charge.voided_at = timezone.now()
    charge.reversal_reference = reversal_reference.strip() if reversal_reference else None
    charge.save()
    from apps.audit.models import AuditLog
    AuditLog.objects.create(actor_user=actor, action_performed="Tuition charge voided", target_table="student_charge", target_record_id=charge.pk)
    return charge
