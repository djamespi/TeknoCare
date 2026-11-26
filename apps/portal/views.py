import json

from django.contrib.auth import login, logout
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.audit.models import AuditLog
from apps.appointments.booking_views import _bookable_slots
from apps.clinical.models import Referral
from apps.common.permissions import active_user, require_permission
from apps.login.forms import LoginForm
from apps.register.forms import RegistrationForm

from .actions import ACTIONS, validated
from .data import portal_data


SCHEDULE_TABLES = {"appointment", "slot", "clinic_room", "provider", "user"}
ENCOUNTER_TABLES = SCHEDULE_TABLES | {
    "patient", "patient_allergy", "medical_record", "vital_sign", "record_diagnosis",
    "prescription", "prescription_item", "referral",
}
ACTION_TABLES = {
    "profile": {"user_profile"},
    "preferences": {"user_settings"},
    "birth-date": {"patient"},
    "contact": {"emergency_contact"},
    "remove-contact": {"emergency_contact"},
    "book": SCHEDULE_TABLES,
    "cancel-booking": SCHEDULE_TABLES,
    "appointment-status": ENCOUNTER_TABLES,
    "open-encounter": ENCOUNTER_TABLES,
    "finalize": ENCOUNTER_TABLES,
    "save-notes": {"medical_record"},
    "change-diagnosis": {"medical_record", "record_diagnosis"},
    "save-vitals": {"medical_record", "vital_sign"},
    "add-prescription-item": {"prescription", "prescription_item"},
    "delete-prescription-item": {"prescription", "prescription_item"},
    "prescription-status": {"prescription", "prescription_item"},
    "referral": {"referral"},
    "add-provider": {"user", "provider"},
    "account-status": {"user", "provider", "slot"},
    "change-charge": {"student_charge"},
    "add-slots": SCHEDULE_TABLES,
    "toggle-slot": SCHEDULE_TABLES,
}


def action_patch(actor, name, values):
    if name == "save-reference":
        table = values["table"]
        tables = {"clinic_room", "slot"} if table == "clinic_room" else {table}
    else:
        tables = ACTION_TABLES.get(name)
    if tables is None:
        return None
    if actor.is_staff:
        tables = tables | {"audit_log"}
    patch = {"db": portal_data(actor, tables)}
    if actor.is_staff and "referral" in tables:
        patch["open_referrals"] = Referral.objects.filter(status=Referral.Status.PENDING).count()
    return patch


@never_cache
@require_GET
def index(request):
    return render(request, "portal/index.html")


def session_snapshot(request):
    actor = active_user(request.user)
    data = portal_data(actor) if actor else None
    demo = getattr(settings, "TEKNOCARE_MAKE_DEMO", False)
    next_open = None
    if demo and not actor:
        selected = _bookable_slots().order_by("start_time", "pk").first()
        if selected:
            next_open = {"start": selected.start_time, "provider": selected.provider.provider.get_full_name()}
    open_referrals = Referral.objects.filter(status=Referral.Status.PENDING).count() if actor and actor.is_staff else 0
    return {"actor": actor.pk if actor else None, "db": data, "csrf": get_token(request),
            "demo": demo, "next_open": next_open, "open_referrals": open_referrals}


@never_cache
@require_GET
def snapshot(request):
    return JsonResponse(session_snapshot(request))


@never_cache
@require_POST
def action(request, name):
    try:
        if request.content_type != "application/json" or len(request.body) > 64_000:
            return JsonResponse({"error": "Send a valid clinic request."}, status=400)
        values = json.loads(request.body)
        if not isinstance(values, dict):
            return JsonResponse({"error": "Send a valid clinic request."}, status=400)
        response = {"result": None}
        with transaction.atomic():
            if name == "login":
                form = LoginForm(values, request=request)
                validated(form)
                if request.user.is_authenticated:
                    raise ValidationError("Sign out before opening another account.")
                login(request, form.user)
                AuditLog.objects.create(actor_user=form.user, action_performed="Account signed in",
                                        target_table="user", target_record_id=form.user.pk)
            elif name == "register":
                if request.user.is_authenticated:
                    raise PermissionDenied
                form = RegistrationForm(values)
                if not form.is_valid():
                    field_errors = {field: list(messages) for field, messages in form.errors.items()}
                    return JsonResponse({
                        "error": " ".join(message for messages in field_errors.values() for message in messages),
                        "field_errors": field_errors,
                    }, status=400)
                form.save()
            elif name == "logout":
                logout(request)
            else:
                actor = require_permission(request.user, "account.use")
                operation = ACTIONS.get(name)
                if operation is None:
                    return JsonResponse({"error": "This action is unavailable."}, status=404)
                response["result"] = operation(actor, values)
                response["patch"] = action_patch(actor, name, values)
            # Serialize while the transaction can still roll back if the response cannot be built.
            return JsonResponse(response)
    except ValidationError as error:
        return JsonResponse({"error": " ".join(error.messages)}, status=400)
    except PermissionDenied:
        return JsonResponse({"error": "You do not have access to this action."}, status=403)
    except ObjectDoesNotExist:
        return JsonResponse({"error": "This record is unavailable."}, status=404)
    except (ValueError, TypeError, KeyError, OverflowError):
        return JsonResponse({"error": "Check the submitted values and try again."}, status=400)
    except IntegrityError:
        return JsonResponse({"error": "The database changed. Reload the page and review the current values."}, status=409)
