from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.appointments.models import Appointment
from apps.appointments.services import cancel_appointment
from apps.common.permissions import allowed, clinical_provider, require_permission
from apps.common.web import add_form_errors
from apps.patients.forms import UniversityIDForm
from apps.patients.models import Patient
from apps.providers.models import Provider
from apps.register.identity import identity_matches
from apps.register.models import User

from .forms import AssignmentForm, AttendingProviderForm
from .models import MedicalRecord
from .reception import (
    assign_encounter, can_check_in, can_mark_no_show, change_appointment_status,
    open_scheduled_encounter, open_walkin_encounter,
)


def _visible_appointments(actor):
    appointments = Appointment.objects.select_related("patient__patient", "slot__provider__provider", "slot__room")
    if actor.is_staff:
        return appointments
    provider = clinical_provider(actor)
    scope = Q(slot__provider_id=actor.pk)
    if provider and provider.provider_type == Provider.Type.NURSE:
        today = timezone.localdate()
        scope |= Q(slot__start_time__date__lte=today, slot__end_time__date__gte=today)
    return appointments.filter(scope).exclude(patient_id=actor.pk)


def _visible_encounters(actor):
    encounters = MedicalRecord.objects.select_related(
        "patient__patient", "provider__provider", "appointment__slot__provider__provider",
    ).defer("chief_complaint", "symptoms", "examination_notes", "treatment_plan")
    if actor.is_staff:
        return encounters
    provider = clinical_provider(actor)
    scope = Q(provider_id=actor.pk)
    if provider and provider.provider_type == Provider.Type.NURSE:
        scope |= Q(visited_at__date=timezone.localdate(), status=MedicalRecord.Status.DRAFT)
    return encounters.filter(scope).exclude(patient_id=actor.pk)


@login_required
@require_http_methods(["GET"])
def queue(request):
    actor = require_permission(request.user, "reception.access")
    today = timezone.localdate()
    drafts = request.GET.get("view") == "drafts"
    if drafts:
        items = _visible_encounters(actor).filter(
            status=MedicalRecord.Status.DRAFT, visited_at__date=today,
        ).order_by("visited_at", "pk")
    else:
        items = _visible_appointments(actor).filter(slot__start_time__date__lte=today).filter(
            Q(slot__end_time__date__gte=today) | Q(status__in=(Appointment.Status.SCHEDULED, Appointment.Status.CHECKED_IN)),
        ).order_by("slot__start_time", "pk")
    query = request.GET.get("q", "").strip()[:150]
    if query:
        items = items.alias(full_name=Concat("patient__patient__fname", Value(" "), "patient__patient__lname")).filter(
            Q(full_name__icontains=query) | Q(patient__patient__school_id__icontains=query)
        )
    return render(request, "clinical/reception_queue.html", {
        "today": today, "drafts": drafts, "page_obj": Paginator(items, 10).get_page(request.GET.get("page")),
        "query": query, "can_walkin": allowed(actor, "reception.walkin"),
    })


@login_required
@require_http_methods(["GET", "POST"])
def appointment(request, pk):
    actor = require_permission(request.user, "reception.access")
    item = get_object_or_404(_visible_appointments(actor), pk=pk)
    may_assign = allowed(actor, "reception.assign")
    existing = MedicalRecord.objects.filter(appointment_id=pk).values("pk", "status").first()
    opening = request.method == "POST" and request.POST.get("action") == "open"
    form = AttendingProviderForm(
        request.POST if opening else None, patient_id=item.patient_id, fixed=not may_assign,
        initial={"provider": item.slot.provider_id},
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if opening and form.is_valid():
            try:
                visit = open_scheduled_encounter(actor=actor, appointment_id=pk, provider_id=form.cleaned_data["provider"].pk)
            except ValidationError as error:
                add_form_errors(form, error)
            else:
                messages.success(request, "Draft encounter opened.")
                return redirect("reception:encounter", pk=visit.pk)
        elif not opening:
            try:
                if action == "cancel" and actor.is_staff:
                    cancel_appointment(actor=actor, appointment_id=pk)
                else:
                    change_appointment_status(actor=actor, appointment_id=pk, action=action)
            except ValidationError as error:
                messages.error(request, error.messages[0])
            else:
                messages.success(request, "Appointment status updated.")
            return redirect("reception:appointment", pk=pk)

    now = timezone.now()
    existing_visible = existing and _visible_encounters(actor).filter(pk=existing["pk"]).exists()
    return render(request, "clinical/reception_appointment.html", {
        "appointment": item, "form": form,
        "can_check_in": can_check_in(item, now),
        "can_no_show": can_mark_no_show(item, now) and not existing,
        "can_cancel": actor.is_staff and item.can_cancel,
        "can_open": item.status == Appointment.Status.CHECKED_IN and not existing,
        "can_complete": item.status == Appointment.Status.CHECKED_IN and existing and existing["status"] == MedicalRecord.Status.FINALIZED,
        "existing": existing if existing_visible else None,
    })


@login_required
@require_http_methods(["GET"])
def walkin_lookup(request):
    require_permission(request.user, "reception.walkin")
    form = UniversityIDForm(request.GET if request.GET else None)
    patient = None
    if form.is_valid():
        accounts = identity_matches(User.objects.filter(account_status=User.AccountStatus.ACTIVE),
            school_id=form.cleaned_data["school_id"])
        patient = Patient.objects.select_related("patient").filter(patient__in=accounts).first()
        if patient is None:
            form.add_error(None, "No active patient matches that University ID.")
    return render(request, "clinical/reception_walkin.html", {"lookup": True, "form": form, "patient": patient})


@login_required
@require_http_methods(["GET", "POST"])
def walkin_create(request, pk):
    actor = require_permission(request.user, "reception.walkin")
    patient = get_object_or_404(Patient.objects.select_related("patient"), pk=pk,
        patient__account_status=User.AccountStatus.ACTIVE)
    form = AttendingProviderForm(request.POST if request.method == "POST" else None, patient_id=patient.pk)
    if request.method == "POST" and form.is_valid():
        try:
            visit = open_walkin_encounter(actor=actor, patient_id=pk, provider_id=form.cleaned_data["provider"].pk)
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            messages.success(request, "Walk-in encounter opened.")
            return redirect("reception:encounter", pk=visit.pk)
    return render(request, "clinical/reception_walkin.html", {"patient": patient, "form": form})


@login_required
@require_http_methods(["GET", "POST"])
def encounter(request, pk):
    actor = require_permission(request.user, "reception.access")
    visit = get_object_or_404(_visible_encounters(actor), pk=pk)
    form = None
    if request.method == "POST":
        require_permission(actor, "reception.assign")
    if allowed(actor, "reception.assign") and visit.status == MedicalRecord.Status.DRAFT:
        form = AssignmentForm(request.POST if request.method == "POST" else None, patient_id=visit.patient_id,
            initial={"provider": visit.provider_id, "expected_provider_id": visit.provider_id})
        if request.method == "POST" and form.is_valid():
            try:
                assign_encounter(actor=actor, record_id=pk, provider_id=form.cleaned_data["provider"].pk,
                    expected_provider_id=form.cleaned_data["expected_provider_id"])
            except ValidationError as error:
                add_form_errors(form, error)
            else:
                messages.success(request, "Attending provider saved.")
                return redirect("reception:encounter", pk=pk)
    elif request.method == "POST":
        messages.error(request, "Only Draft encounters can be reassigned.")
        return redirect("reception:encounter", pk=pk)
    clinical_access = visit.patient_id != actor.pk and allowed(actor, "consultation.access") and (
        allowed(actor, "record.view", visit) or allowed(actor, "vitals.record", visit)
    )
    return render(request, "clinical/reception_encounter.html", {
        "visit": visit, "form": form, "clinical_access": clinical_access,
    })
