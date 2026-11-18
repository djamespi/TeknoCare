from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.appointments.models import Appointment, Slot
from apps.audit.models import AuditLog
from apps.clinical.models import MedicalRecord
from apps.common.permissions import require_permission
from apps.register.models import User
from .models import Provider


@transaction.atomic
def attach_provider_profile(*, actor, user_id):
    actor = require_permission(actor, "accounts.manage")
    user = User.objects.select_for_update().get(pk=user_id)
    if user.user_type not in {"Admin", "Provider"}:
        raise ValidationError({"user": "Only an Admin/Provider account can receive a Provider profile."})
    if Provider.objects.filter(pk=user.pk).exists():
        raise ValidationError({"user": "That account already has a Provider profile."})
    provider = Provider.objects.create(provider=user, provider_type=Provider.Type.UNVERIFIED, is_active=False)
    AuditLog.objects.create(actor_user=actor, action_performed="Provider profile attached", target_table="provider", target_record_id=provider.pk)
    return provider


@transaction.atomic
def save_provider(*, actor, provider_id, provider_type, license_number, specialization, is_active, verification_confirmed=False):
    actor = require_permission(actor, "reference.manage")
    user = User.objects.select_for_update().get(pk=provider_id)
    provider = Provider.objects.select_for_update().get(pk=provider_id)
    slot_ids = list(provider.slots.select_for_update().order_by("pk").values_list("pk", flat=True))
    designation_changed = provider.provider_type != provider_type
    if (is_active or designation_changed) and not verification_confirmed:
        raise ValidationError({"verification_confirmed": "Confirm review before activation or changing the designation."})
    if is_active and (provider_type == Provider.Type.UNVERIFIED or not user.is_active or user.user_type not in {"Admin", "Provider"}):
        raise ValidationError({"is_active": "Activation requires a known designation and an Active Admin/Provider account."})
    if designation_changed and provider.provider_type != Provider.Type.UNVERIFIED:
        if slot_ids or provider.medical_records.exists() or provider.prescriptions.exists() or provider.referrals.exists():
            raise ValidationError({"provider_type": "A referenced designation needs a separate reviewed correction workflow; history was not rewritten."})
    if provider.is_active and not is_active:
        if Appointment.objects.filter(slot_id__in=slot_ids, status__in=["Scheduled", "Checked-In"]).exists() or MedicalRecord.objects.filter(provider=provider, status="Draft").exists():
            raise ValidationError("Resolve live bookings and Draft encounters before clinical deactivation. No visits were deleted or reassigned.")
    if not is_active:
        Slot.objects.filter(pk__in=slot_ids, end_time__gt=timezone.now(), is_active=True).update(is_active=False)
    provider.provider_type = provider_type
    provider.license_number = (license_number or "").strip() or None
    provider.specialization = (specialization or "").strip() or None
    provider.is_active = is_active
    provider.save()
    AuditLog.objects.create(actor_user=actor, action_performed="Provider updated; review confirmed" if verification_confirmed else "Provider updated",
        target_table="provider", target_record_id=provider.pk)
    return provider
