from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.common.permissions import require_permission
from apps.common.web import add_form_errors
from apps.providers.eligibility import eligible_providers

from .forms import AvailabilityFilterForm, SlotForm
from .models import Appointment, Slot, protected_slot_appointments
from .services import save_slot


def _visible_slots(actor):
    linked = Appointment.objects.filter(slot_id=OuterRef("pk"))
    slots = Slot.objects.select_related("provider__provider", "room").annotate(
        has_appointment=Exists(linked),
        has_protected_appointment=Exists(protected_slot_appointments(linked)),
        provider_eligible=Exists(eligible_providers().filter(pk=OuterRef("provider_id"))),
    )
    return slots if actor.is_staff else slots.filter(provider_id=actor.pk)


@login_required
@require_http_methods(["GET"])
def slot_list(request):
    actor = require_permission(request.user, "schedule.access")
    form = AvailabilityFilterForm(request.GET, admin=actor.is_staff)
    slots = _visible_slots(actor).order_by("-start_time", "pk")
    if form.is_valid():
        values = form.cleaned_data
        if values["from_date"]:
            slots = slots.filter(start_time__date__gte=values["from_date"])
        if values["through_date"]:
            slots = slots.filter(start_time__date__lte=values["through_date"])
        if values.get("provider"):
            slots = slots.filter(provider=values["provider"])
    else:
        slots = slots.none()
    return render(request, "appointments/slot_list.html", {
        "filter_form": form, "page_obj": Paginator(slots, 10).get_page(request.GET.get("page")), "now": timezone.now(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def slot_edit(request, pk=None):
    actor = require_permission(request.user, "schedule.access")
    slot = get_object_or_404(_visible_slots(actor), pk=pk) if pk is not None else None
    now = timezone.now()
    read_only = slot and (slot.start_time <= now or slot.has_protected_appointment)
    form = None
    if not read_only:
        form = SlotForm(request.POST if request.method == "POST" else None, admin=actor.is_staff, slot=slot)
        if request.method == "POST" and form.is_valid():
            values = form.cleaned_data
            try:
                save_slot(
                    actor=actor, slot_id=pk, expected_version=values.get("expected_version"),
                    provider_id=values["provider"].pk if actor.is_staff else actor.pk,
                    room_id=values["room"].pk if values["room"] else None,
                    start_time=values["start_time"], end_time=values["end_time"], is_active=values["is_active"],
                )
            except ValidationError as error:
                add_form_errors(form, error)
            except IntegrityError as error:
                constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", None)
                if constraint not in {"slot_no_provider_overlap", "slot_no_room_overlap"}:
                    raise
                form.add_error(None, "The provider or room already has overlapping availability.")
            else:
                messages.success(request, "Availability saved.")
                return redirect("availability:list")
    return render(request, "appointments/slot_form.html", {
        "slot": slot, "form": form, "now": now,
    }, status=409 if read_only and request.method == "POST" else 200)
