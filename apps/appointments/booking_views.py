import sqlite3
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError
from django.db.models import Count, Exists, OuterRef
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.common.permissions import require_permission
from apps.common.web import add_form_errors
from apps.patients.models import Patient
from apps.providers.eligibility import eligible_providers

from .forms import BookingFilterForm, BookingForm
from .models import Appointment, Slot, protected_slot_appointments
from .services import book_appointment, cancel_appointment, reschedule_appointment


def _own_appointments(request):
    user = require_permission(request.user, "account.use")
    patient = get_object_or_404(Patient, pk=user.pk)
    return patient.appointments.select_related("slot__provider__provider", "slot__room")


def _bookable_slots():
    linked = Appointment.objects.filter(slot_id=OuterRef("pk"))
    return Slot.objects.filter(is_active=True, start_time__gt=timezone.now(),
        room__is_active=True, provider__in=eligible_providers()).filter(
        ~Exists(protected_slot_appointments(linked))
    ).select_related("provider__provider", "room")


def _booking_conflict(error):
    cause = error.__cause__
    if getattr(getattr(cause, "diag", None), "constraint_name", None) == "one_live_booking_per_slot":
        return True
    if isinstance(cause, sqlite3.IntegrityError):
        return str(cause) == "UNIQUE constraint failed: appointment.slot_id"
    if isinstance(cause, sqlite3.OperationalError):
        return (getattr(cause, "sqlite_errorcode", 0) & 0xFF) in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
    return False


def _changed_appointment(request, appointment):
    messages.error(request, "Only future Scheduled appointments without a linked visit can be changed.")
    return redirect("booking:detail", appointment_id=appointment.pk)


@login_required
@require_http_methods(["GET"])
def appointment_list(request):
    appointments = _own_appointments(request)
    upcoming = dict(slot__start_time__gt=timezone.now(),
        status__in=(Appointment.Status.SCHEDULED, Appointment.Status.CHECKED_IN))
    history = request.GET.get("view") == "history"
    if history:
        appointments = appointments.exclude(**upcoming).order_by("-slot__start_time", "-pk")
    else:
        appointments = appointments.filter(**upcoming).order_by("slot__start_time", "pk")
    return render(request, "appointments/booking_list.html", {
        "history": history, "page_obj": Paginator(appointments, 10).get_page(request.GET.get("page")),
    })


@login_required
@require_http_methods(["GET"])
def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(_own_appointments(request), pk=appointment_id)
    return render(request, "appointments/booking_detail.html", {"appointment": appointment})


@login_required
@require_http_methods(["GET", "POST"])
def appointment_cancel(request, appointment_id):
    appointment = get_object_or_404(_own_appointments(request), pk=appointment_id)
    if not appointment.can_cancel:
        return _changed_appointment(request, appointment)
    if request.method == "POST":
        try:
            cancel_appointment(actor=request.user, appointment_id=appointment.pk)
        except PermissionDenied:
            return _changed_appointment(request, appointment)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        except OperationalError as error:
            if not _booking_conflict(error):
                raise
            messages.error(request, "The appointment is being updated. Open it again to retry.")
        else:
            messages.success(request, "Appointment canceled.")
        return redirect("booking:detail", appointment_id=appointment.pk)
    return render(request, "appointments/booking_cancel.html", {"appointment": appointment})


@login_required
@require_http_methods(["GET"])
def slot_browse(request, appointment_id=None):
    appointments = _own_appointments(request)
    original = get_object_or_404(appointments, pk=appointment_id) if appointment_id is not None else None
    if original and not original.can_cancel:
        return _changed_appointment(request, original)

    form = BookingFilterForm(request.GET)
    slots = _bookable_slots().order_by("start_time", "pk")
    week = []
    if form.is_valid():
        filters = form.cleaned_data
        if filters["provider"]:
            slots = slots.filter(provider=filters["provider"])
        if filters["provider_type"]:
            slots = slots.filter(provider__provider_type=filters["provider_type"])
        today = timezone.localdate()
        days = [today + timedelta(days=offset) for offset in range(7)]
        counts = dict(slots.filter(start_time__date__range=(days[0], days[-1])).order_by()
                      .annotate(day=TruncDate("start_time")).values_list("day").annotate(count=Count("pk")))
        week = [(day, counts.get(day, 0)) for day in days]
        if filters["date"]:
            slots = slots.filter(start_time__date=filters["date"])
    else:
        slots = slots.none()
    return render(request, "appointments/booking_slots.html", {
        "original": original, "filter_form": form, "week": week,
        "page_obj": Paginator(slots, 10).get_page(request.GET.get("page")),
    })


@login_required
@require_http_methods(["GET", "POST"])
def slot_book(request, slot_id, appointment_id=None):
    appointments = _own_appointments(request)
    original = get_object_or_404(appointments, pk=appointment_id) if appointment_id is not None else None
    if original and not original.can_cancel:
        return _changed_appointment(request, original)

    slot = _bookable_slots().filter(pk=slot_id).first()
    if slot is None:
        messages.error(request, "This slot is no longer open for booking. Choose another time.")
        if original:
            return redirect("booking:reschedule", appointment_id=original.pk)
        return redirect("booking:browse")

    form = BookingForm(request.POST if request.method == "POST" else None, initial={
        "expected_version": slot.version, "reason_for_visit": original.reason_for_visit if original else "",
    })
    if request.method == "POST" and form.is_valid():
        values = {"actor": request.user, "slot_id": slot.pk, **form.cleaned_data}
        try:
            if original:
                appointment = reschedule_appointment(appointment_id=original.pk, **values)
            else:
                appointment = book_appointment(patient_id=request.user.pk, **values)
        except PermissionDenied:
            if not original:
                raise
            return _changed_appointment(request, original)
        except ValidationError as error:
            add_form_errors(form, error)
        except (IntegrityError, OperationalError) as error:
            if not _booking_conflict(error):
                raise
            form.add_error(None, "Availability is being updated. Review the available times and try again.")
        else:
            messages.success(request, "Appointment rescheduled." if original else "Appointment booked.")
            return redirect("booking:detail", appointment_id=appointment.pk)
    return render(request, "appointments/booking_form.html", {"slot": slot, "original": original, "form": form})
