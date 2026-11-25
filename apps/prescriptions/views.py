from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.clinical.models import MedicalRecord
from apps.common.permissions import allowed, require_permission
from apps.common.web import ReferenceFilterForm, add_form_errors, clinic_admin_required
from apps.patients.models import Patient
from apps.portal.entrypoint import portal_ready

from .forms import MedicationForm, PrescriptionActionForm, PrescriptionItemForm, ReplacementForm
from .models import Medication, Prescription
from .services import discard_or_cancel, issue_prescription, prescription_version, remove_item, save_item, save_medication, start_prescription, start_replacement


def _clinical_visit(request, record_id):
    actor = require_permission(request.user, "consultation.access")
    visit = get_object_or_404(MedicalRecord.objects.select_related("patient__patient"), pk=record_id)
    if visit.patient_id == actor.pk or not allowed(actor, "record.view", visit):
        raise Http404
    return actor, visit


def _published():
    return Prescription.objects.filter(status__in=(Prescription.Status.ISSUED, Prescription.Status.CANCELED),
        issued_at__isnull=False)


@login_required
@require_http_methods(["GET"])
@never_cache
def patient_history(request):
    patient = get_object_or_404(Patient, pk=request.user.pk)
    rows = _published().filter(record__patient=patient).select_related("prescriber__provider").order_by("-issued_at", "-pk")
    return render(request, "prescriptions/history.html", {
        "page_obj": Paginator(rows, 10).get_page(request.GET.get("page")),
    })


@login_required
@require_http_methods(["GET"])
@never_cache
def print_detail(request, pk):
    actor = require_permission(request.user, "account.use")
    prescription = get_object_or_404(_published().select_related("record__patient__patient", "prescriber__provider"), pk=pk)
    if prescription.record.patient_id != actor.pk and not allowed(actor, "record.view", prescription.record):
        raise Http404
    return render(request, "prescriptions/print.html", {
        "prescription": prescription, "items": prescription.items.select_related("medication").order_by("pk"),
    })


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def encounter(request, record_id):
    actor, visit = _clinical_visit(request, record_id)
    can_start = allowed(actor, "prescription.issue", visit)
    if request.method == "POST":
        if not can_start:
            raise PermissionDenied
        try:
            draft = start_prescription(actor=actor, record_id=record_id)
        except ValidationError as error:
            messages.error(request, error.messages[0])
            return redirect("prescriptions:encounter", record_id=record_id)
        return redirect("prescriptions:detail", record_id=record_id, pk=draft.pk)
    rows = visit.prescriptions.select_related("prescriber__provider").order_by("-pk")
    if not allowed(actor, "prescription.correct", visit):
        rows = rows.filter(issued_at__isnull=False)
    draft_exists = rows.filter(status=Prescription.Status.DRAFT).exists()
    return render(request, "prescriptions/encounter.html", {
        "visit": visit, "can_start": can_start and not draft_exists,
        "page_obj": Paginator(rows, 10).get_page(request.GET.get("page")),
    })


def _prescription_for_visit(visit, pk, actor):
    prescription = get_object_or_404(visit.prescriptions.select_related("prescriber__provider"), pk=pk)
    if prescription.issued_at is None and not allowed(actor, "prescription.correct", visit):
        raise Http404
    return prescription


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def detail(request, record_id, pk):
    actor, visit = _clinical_visit(request, record_id)
    prescription = _prescription_for_visit(visit, pk, actor)
    items = list(prescription.items.select_related("medication").order_by("pk"))
    version = prescription_version(prescription, items)
    can_edit = (prescription.status == Prescription.Status.DRAFT and prescription.prescriber_id == actor.pk
        and allowed(actor, "prescription.issue", visit))
    can_correct = allowed(actor, "prescription.correct", visit)
    action = request.POST.get("action") if request.method == "POST" else None
    action_forms = {}
    if can_edit:
        action_forms["issue"] = PrescriptionActionForm(request.POST if action == "issue" else None,
            prefix="issue", initial={"expected_version": version})
    if can_correct and prescription.status != Prescription.Status.CANCELED:
        action_forms["cancel"] = PrescriptionActionForm(request.POST if action == "cancel" else None,
            prefix="cancel", initial={"expected_version": version})
    if can_correct and prescription.status == Prescription.Status.CANCELED and prescription.issued_at:
        action_forms["replace"] = ReplacementForm(request.POST if action == "replace" else None,
            patient_id=visit.patient_id, provider_id=actor.pk)
    if request.method == "POST":
        form = action_forms.get(action)
        if form is None:
            raise PermissionDenied
        if form.is_valid():
            try:
                if action == "replace":
                    draft = start_replacement(actor=actor, old_prescription_id=pk, record_id=form.cleaned_data["encounter"].pk)
                    messages.success(request, "Replacement draft opened. Review it before issuing.")
                    return redirect("prescriptions:detail", record_id=draft.record_id, pk=draft.pk)
                operation = issue_prescription if action == "issue" else discard_or_cancel
                operation(actor=actor, record_id=record_id, prescription_id=pk,
                    expected_version=form.cleaned_data["expected_version"])
            except ValidationError as error:
                add_form_errors(form, error)
            else:
                messages.success(request, "Prescription issued." if action == "issue" else "Prescription canceled.")
                return redirect("prescriptions:detail", record_id=record_id, pk=pk)
    return render(request, "prescriptions/detail.html", {
        "visit": visit, "prescription": prescription, "items": items, "can_edit": can_edit, "version": version,
        "issue_form": action_forms.get("issue"), "cancel_form": action_forms.get("cancel"),
        "replacement_form": action_forms.get("replace"),
    })


def _editable_prescription(request, record_id, pk):
    actor, visit = _clinical_visit(request, record_id)
    prescription = _prescription_for_visit(visit, pk, actor)
    if (not allowed(actor, "prescription.issue", visit)
        or prescription.status != Prescription.Status.DRAFT or prescription.prescriber_id != actor.pk):
        raise PermissionDenied
    return actor, prescription


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def item_edit(request, record_id, pk, item_id=None):
    actor, prescription = _editable_prescription(request, record_id, pk)
    item = get_object_or_404(prescription.items, pk=item_id) if item_id else None
    form = PrescriptionItemForm(request.POST if request.method == "POST" else None, instance=item,
        initial={"expected_version": prescription_version(prescription, prescription.items.all())})
    if request.method == "POST" and form.is_valid():
        try:
            save_item(actor=actor, record_id=record_id, prescription_id=pk, item_id=item_id,
                expected_version=form.cleaned_data["expected_version"], medication_id=form.cleaned_data["medication"].pk,
                values=form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            return redirect("prescriptions:detail", record_id=record_id, pk=pk)
    return render(request, "prescriptions/item_form.html", {"form": form, "prescription": prescription, "item": item})


@login_required
@require_http_methods(["POST"])
@never_cache
def item_remove(request, record_id, pk, item_id):
    actor, prescription = _editable_prescription(request, record_id, pk)
    get_object_or_404(prescription.items, pk=item_id)
    try:
        remove_item(actor=actor, record_id=record_id, prescription_id=pk, item_id=item_id,
            expected_version=request.POST.get("expected_version", ""))
    except ValidationError as error:
        messages.error(request, error.messages[0])
    return redirect("prescriptions:detail", record_id=record_id, pk=pk)


@clinic_admin_required
@require_http_methods(["GET"])
def medication_list(request):
    form = ReferenceFilterForm(request.GET)
    entries = Medication.objects.order_by("generic_name", "medication_code")
    if form.is_valid():
        query = form.cleaned_data["q"]
        entries = entries.filter(Q(medication_code__icontains=query) | Q(generic_name__icontains=query))
        if form.cleaned_data["state"]:
            entries = entries.filter(is_active=form.cleaned_data["state"] == "active")
    else:
        entries = entries.none()
    return render(request, "prescriptions/catalog.html", {
        "filter_form": form, "page_obj": Paginator(entries, 10).get_page(request.GET.get("page")),
    })


@login_required
@require_http_methods(["GET"])
def formulary(request):
    require_permission(request.user, "consultation.access")
    if not request.GET and portal_ready():
        return redirect(reverse("portal:index") + "#/formulary")
    form = ReferenceFilterForm(request.GET)
    entries = Medication.objects.order_by("generic_name", "strength", "medication_code")
    totals = entries.aggregate(
        medications=Count("pk"),
        active=Count("pk", filter=Q(is_active=True)),
        forms=Count("dosage_form", distinct=True),
    )
    if form.is_valid():
        query = form.cleaned_data["q"]
        entries = entries.filter(
            Q(medication_code__icontains=query) | Q(generic_name__icontains=query)
            | Q(dosage_form__icontains=query) | Q(strength__icontains=query),
        )
        if state := form.cleaned_data["state"]:
            entries = entries.filter(is_active=state == "active")
    else:
        entries = entries.none()
    return render(request, "prescriptions/formulary.html", {
        "filter_form": form, "totals": totals,
        "page_obj": Paginator(entries, 16).get_page(request.GET.get("page")),
    })


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def medication_edit(request, pk=None):
    entry = get_object_or_404(Medication, pk=pk) if pk else None
    form = MedicationForm(request.POST if request.method == "POST" else None, instance=entry)
    if request.method == "POST" and form.is_valid():
        try:
            save_medication(actor=request.user, medication_id=pk, values=form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "The entry changed or its code is already in use. Reload and review the catalog.")
        else:
            messages.success(request, "Medication catalog entry saved.")
            return redirect("prescriptions:catalog")
    return render(request, "includes/management_form.html", {
        "form": form, "title": "Edit medication" if pk else "Add medication",
        "description": "Enter reviewed or fictional catalog details. Referenced formulations retain their code and identity. Deactivate entries to prevent new selection.",
        "back_url": "prescriptions:catalog",
    })
