from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.clinical.models import MedicalRecord
from apps.common.permissions import require_permission
from apps.common.web import add_form_errors
from apps.patients.forms import UniversityIDForm
from apps.patients.models import Affiliation, Patient
from apps.register.identity import identity_matches
from apps.register.models import User

from .exports import pending_csv
from .forms import ChargeCreateForm, ChargeFilterForm, SimulatedPostingForm, TermFilterForm, VoidChargeForm
from .models import StudentCharge
from .services import create_charge, is_simulated_posting, simulate_posting, simulate_void


def _ordered_charges():
    return StudentCharge.objects.select_related("term").order_by("-created_at", "-pk")


def _admin_charges():
    return _ordered_charges().select_related("record__patient__patient").only(
        "charge_code", "description", "amount", "currency_code", "status", "billing_reference",
        "reversal_reference", "posted_at", "voided_at", "void_reason", "record__status",
        "record__patient__patient__school_id", "term__academic_year", "term__semester",
        "term__is_open_for_charges",
    )


def _filtered_charges(charges, form):
    if not form.is_valid():
        return charges.none()
    if form.cleaned_data["term"]:
        charges = charges.filter(term=form.cleaned_data["term"])
    if status := form.cleaned_data.get("status"):
        charges = charges.filter(status=status)
    return charges


@login_required
@require_http_methods(["GET"])
@never_cache
def charge_list(request):
    require_permission(request.user, "billing.manage")
    form = ChargeFilterForm(request.GET)
    charges = _filtered_charges(_admin_charges(), form)
    term = form.cleaned_data.get("term")
    return render(request, "billing/charges.html", {
        "admin_view": True, "filter_form": form, "export_term": term.pk if term else None,
        "page_obj": Paginator(charges, 10).get_page(request.GET.get("page")),
    })


@login_required
@require_http_methods(["GET"])
@never_cache
def charge_lookup(request):
    require_permission(request.user, "billing.manage")
    form = UniversityIDForm(request.GET or None)
    visits = MedicalRecord.objects.none()
    if form.is_valid():
        accounts = identity_matches(User.objects.all(), school_id=form.cleaned_data["school_id"])
        visits = MedicalRecord.objects.filter(patient__patient__in=accounts).only(
            "pk", "visited_at", "status", "affiliation_at_visit",
        ).order_by("-visited_at", "-pk")
    return render(request, "billing/charge_lookup.html", {
        "form": form, "page_obj": Paginator(visits, 10).get_page(request.GET.get("page")),
    })


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def charge_create(request, record_id):
    actor = require_permission(request.user, "billing.manage")
    visit = get_object_or_404(MedicalRecord.objects.select_related("patient__patient").only(
        "pk", "status", "affiliation_at_visit", "patient__patient__school_id",
    ), pk=record_id)
    form = None
    if visit.affiliation_at_visit == Affiliation.STUDENT:
        form = ChargeCreateForm(request.POST if request.method == "POST" else None, initial={"request_code": uuid4()})
        if request.method == "POST" and form.is_valid():
            values = form.cleaned_data
            try:
                charge = create_charge(actor=actor, record_id=record_id, term_id=values["term"].pk,
                    description=values["description"], amount=values["amount"], request_code=values["request_code"])
            except ValidationError as error:
                add_form_errors(form, error)
            except IntegrityError:
                form.add_error(None, "The charge could not be saved. Reload and review the encounter and term.")
            else:
                messages.success(request, "Charge recorded in the prototype.")
                return redirect("billing:charge_detail", pk=charge.pk)
    return render(request, "billing/charge_form.html", {"visit": visit, "form": form, "currency": settings.CLINIC_CURRENCY_CODE})


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def charge_detail(request, pk):
    actor = require_permission(request.user, "billing.manage")
    charge = get_object_or_404(_admin_charges(), pk=pk)
    action = request.POST.get("action") if request.method == "POST" else None
    posting = SimulatedPostingForm(request.POST if action == "post" else None, prefix="post")
    voiding = VoidChargeForm(request.POST if action == "void" else None, prefix="void",
        posted=charge.status == StudentCharge.Status.POSTED, initial={"expected_status": charge.status})
    if request.method == "POST":
        if action not in {"post", "void"}:
            return HttpResponseBadRequest("Choose a charge action.")
        form = posting if action == "post" else voiding
        if form.is_valid():
            operation = simulate_posting if action == "post" else simulate_void
            values = form.cleaned_data.copy()
            values["confirmed"] = values.pop("confirm")
            try:
                result = operation(charge_id=pk, actor=actor, **values)
            except ValidationError as error:
                add_form_errors(form, error)
            else:
                if action == "post":
                    messages.success(request, "Simulated acknowledgment recorded. Charge status is Posted.")
                elif result.reversal_reference:
                    messages.success(request, "Simulated reversal recorded. Charge status is Voided.")
                else:
                    messages.success(request, "Pending charge voided.")
                return redirect("billing:charge_detail", pk=pk)
    return render(request, "billing/charge_detail.html", {
        "charge": charge, "admin_view": True, "posting": posting, "voiding": voiding,
        "can_post": charge.status == StudentCharge.Status.PENDING and charge.record.status == MedicalRecord.Status.FINALIZED
            and charge.term.is_open_for_charges,
        "can_void": charge.status == StudentCharge.Status.PENDING or (
            charge.status == StudentCharge.Status.POSTED and is_simulated_posting(charge)),
        "simulated_posting": is_simulated_posting(charge),
    })


@login_required
@require_http_methods(["GET"])
@never_cache
def charge_export(request):
    require_permission(request.user, "billing.manage")
    form = TermFilterForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest("Choose a valid academic term.")
    charges = _filtered_charges(StudentCharge.objects.filter(status=StudentCharge.Status.PENDING).order_by("pk"), form)
    return pending_csv(charges)


def _patient_charges(request):
    actor = require_permission(request.user, "account.use")
    patient = get_object_or_404(Patient, pk=actor.pk)
    return patient, _ordered_charges().filter(record__patient=patient)


@login_required
@require_http_methods(["GET"])
@never_cache
def patient_charge_list(request):
    patient, charges = _patient_charges(request)
    form = ChargeFilterForm(request.GET)
    charges = _filtered_charges(charges, form)
    return render(request, "billing/charges.html", {
        "patient": patient, "filter_form": form,
        "page_obj": Paginator(charges, 10).get_page(request.GET.get("page")),
    })


@login_required
@require_http_methods(["GET"])
@never_cache
def patient_charge_detail(request, pk):
    _, charges = _patient_charges(request)
    charge = get_object_or_404(charges, pk=pk)
    return render(request, "billing/charge_detail.html", {"charge": charge, "simulated_posting": is_simulated_posting(charge)})
