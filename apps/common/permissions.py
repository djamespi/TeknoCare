"""Explicit prototype access rules; action checks do not replace scoped queries."""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone


def active_user(actor):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "pk", None):
        return None
    return get_user_model().objects.filter(pk=actor.pk, account_status="Active").first()


def required_profile_exists(user):
    from apps.patients.models import Patient
    from apps.providers.models import Provider
    if user.user_type == "Patient":
        return Patient.objects.filter(pk=user.pk).exists()
    if user.user_type == "Provider":
        return Provider.objects.filter(pk=user.pk).exists()
    return user.user_type == "Admin"


def clinical_provider(user):
    from apps.providers.models import Provider
    if user.user_type not in {"Admin", "Provider"}:
        return None
    return Provider.objects.filter(pk=user.pk, is_active=True, provider_type__in=["Physician", "Dentist", "Nurse"]).first()


def patient_under_care(provider, patient):
    return (
        patient.medical_records.filter(provider=provider, status="Draft").exists()
        or patient.appointments.filter(slot__provider=provider, slot__end_time__gte=timezone.now(), status__in=["Scheduled", "Checked-In"]).exists()
    )


def _clinical_patient_access(provider, patient):
    return bool(provider and (
        patient_under_care(provider, patient)
        or (
            provider.provider_type == "Nurse"
            and patient.medical_records.filter(status="Draft", visited_at__date=timezone.localdate()).exists()
        )
    ))


def allowed(user, action, target=None):
    if not user or not required_profile_exists(user):
        return False
    is_admin = user.user_type == "Admin"
    if action in {"accounts.manage", "reference.manage", "billing.manage", "audit.view"}:
        return is_admin
    if action == "account.use":
        return True
    if action == "patient.allergy_lookup":
        return bool(clinical_provider(user))
    if target is None:
        return False
    if action == "appointment.book":
        return target.patient.is_active and (is_admin or target.pk == user.pk)
    if action == "appointment.cancel":
        return (
            (is_admin or target.patient_id == user.pk)
            and target.status == "Scheduled" and target.slot.start_time > timezone.now()
            and not hasattr(target, "medical_record")
        )
    provider = clinical_provider(user)
    if action == "schedule.manage":
        return is_admin or bool(provider and provider.pk == target.pk)
    if action == "patient.view":
        return is_admin or target.pk == user.pk or _clinical_patient_access(provider, target)
    if action == "patient.allergy_edit":
        return target.pk != user.pk and _clinical_patient_access(provider, target)
    if action == "record.view":
        if target.patient_id == user.pk:
            return target.status == "Finalized"
        return bool(provider and provider.provider_type in {"Physician", "Dentist"} and (
            target.provider_id == provider.pk
            or (provider.provider_type in {"Physician", "Dentist"} and target.status == "Finalized" and patient_under_care(provider, target.patient))
        ))
    if action in {"vitals.record", "record.finalize", "prescription.issue"}:
        if not provider or target.patient_id == user.pk or target.status != "Draft":
            return False
        if action == "vitals.record":
            return target.provider_id == provider.pk or (provider.provider_type == "Nurse" and timezone.localtime(target.visited_at).date() == timezone.localdate())
        return target.provider_id == provider.pk and provider.provider_type in {"Physician", "Dentist"}
    return False


def can(actor, action, target=None):
    return allowed(active_user(actor), action, target)


def require_permission(actor, action, target=None):
    user = active_user(actor)
    if not allowed(user, action, target):
        raise PermissionDenied("You do not have access to this action.")
    return user
