"""Authorized transactional account provisioning and credential changes."""
from django.contrib.auth.password_validation import password_changed, validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.common.permissions import require_permission
from apps.patients.models import Affiliation, EmergencyContact, Patient
from apps.providers.models import Provider
from .identity import identity_matches, normalize_email, normalize_school_id
from .models import User


def _audit(actor, action, user):
    AuditLog.objects.create(actor_user=actor, action_performed=action, target_table="user", target_record_id=user.pk)


def _new_user(*, school_id, email, first_name, last_name, password, role):
    school_id = normalize_school_id(school_id)
    email = normalize_email(email)
    if identity_matches(User.objects.all(), school_id=school_id).exists():
        raise ValidationError({"school_id": "That University ID is already registered."})
    if identity_matches(User.objects.all(), email=email).exists():
        raise ValidationError({"email": "That email is already registered."})
    user = User(school_id=school_id, email=email, fname=first_name.strip(), lname=last_name.strip(),
        user_type=role, account_status=User.AccountStatus.ACTIVE)
    validate_password(password, user)
    user.set_password(password)
    user.full_clean()
    user.save()
    return user


@transaction.atomic
def register_student(*, school_id, email, first_name, last_name, password,
    contact_name, contact_relationship, contact_phone, medical_history_summary=""):
    user = _new_user(school_id=school_id, email=email, first_name=first_name, last_name=last_name,
        password=password, role=User.UserType.PATIENT)
    patient = Patient.objects.create(patient=user, affiliation=Affiliation.STUDENT, medical_history_summary=medical_history_summary)
    EmergencyContact.objects.create(patient=patient, full_name=contact_name.strip(), relationship=contact_relationship.strip(),
        phone_number=contact_phone.strip(), is_primary=True)
    _audit(user, "Student account registered", user)
    return user


@transaction.atomic
def create_personnel_account(*, actor, school_id, email, first_name, last_name, password, affiliation, department=None):
    actor = require_permission(actor, "accounts.manage")
    if affiliation not in {Affiliation.FACULTY, Affiliation.STAFF}:
        raise ValidationError({"affiliation": "Choose Faculty or Staff for personnel intake."})
    user = _new_user(school_id=school_id, email=email, first_name=first_name, last_name=last_name,
        password=password, role=User.UserType.PATIENT)
    Patient.objects.create(patient=user, affiliation=affiliation, department=department)
    _audit(actor, "Personnel account provisioned", user)
    return user


@transaction.atomic
def create_provider_account(*, actor, school_id, email, first_name, last_name, password,
    provider_type=Provider.Type.UNVERIFIED, license_number=None, specialization=None):
    actor = require_permission(actor, "accounts.manage")
    user = _new_user(school_id=school_id, email=email, first_name=first_name, last_name=last_name,
        password=password, role=User.UserType.PROVIDER)
    Provider.objects.create(provider=user, provider_type=provider_type,
        license_number=(license_number or "").strip() or None, specialization=specialization, is_active=False)
    _audit(actor, "Provider account provisioned", user)
    return user


@transaction.atomic
def add_patient_profile(*, actor, user_id, affiliation, department=None, date_of_birth=None):
    actor = require_permission(actor, "accounts.manage")
    user = User.objects.select_for_update().get(pk=user_id)
    if Patient.objects.filter(pk=user.pk).exists():
        raise ValidationError("This account already has a patient profile; use the patient correction workflow.")
    patient = Patient.objects.create(patient=user, affiliation=affiliation, department=department, date_of_birth=date_of_birth)
    _audit(actor, "Patient profile provisioned", user)
    return patient


def _credential_target(actor, user):
    if user.pk == actor.pk or user.user_type == User.UserType.ADMIN:
        raise PermissionDenied("Use your own password-change page; other Admin recovery requires the trusted server operator.")


def _set_password(user, new_password):
    try:
        validate_password(new_password, user)
    except ValidationError as error:
        raise ValidationError({"new_password1": error.messages}) from None
    user.set_password(new_password)
    user.save(update_fields=["password_hash"])
    password_changed(new_password, user)


@transaction.atomic
def change_password(*, actor, old_password, new_password):
    actor = require_permission(actor, "account.use")
    user = User.objects.select_for_update().get(pk=actor.pk)
    if not user.check_password(old_password):
        raise ValidationError({"old_password": "Your current password is incorrect."})
    _set_password(user, new_password)
    _audit(user, "Account password changed", user)
    return user


@transaction.atomic
def reset_account_password(*, actor, school_id, admin_password, new_password):
    actor = require_permission(actor, "accounts.manage")
    actor = User.objects.select_for_update().get(pk=actor.pk)
    if not actor.check_password(admin_password):
        raise ValidationError({"admin_password": "Your administrator password is incorrect."})
    user = identity_matches(User.objects.select_for_update(), school_id=school_id).first()
    if not user:
        raise ValidationError({"university_id": "No account matches that University ID."})
    _credential_target(actor, user)
    _set_password(user, new_password)
    _audit(actor, "Account password reset by Admin", user)
    return user


@transaction.atomic
def set_account_status(*, actor, user_id, status):
    actor = require_permission(actor, "accounts.manage")
    user = User.objects.select_for_update().get(pk=user_id)
    _credential_target(actor, user)
    if status not in User.AccountStatus.values:
        raise ValidationError({"account_status": "Choose Active or Suspended."})
    user.account_status = status
    user.save(update_fields=["account_status"])
    if status == User.AccountStatus.SUSPENDED:
        session_keys = [session.session_key for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator()
            if session.get_decoded().get("_auth_user_id") == str(user.pk)]
        Session.objects.filter(session_key__in=session_keys).delete()
    _audit(actor, f"Account status set to {status}", user)
    return user
