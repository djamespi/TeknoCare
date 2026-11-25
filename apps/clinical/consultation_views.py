from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.common.permissions import allowed, clinical_provider, patient_under_care, require_permission
from apps.common.web import add_form_errors, clinic_admin_required
from apps.providers.models import Provider

from .consultation import NOTE_FIELDS, consultation_version, create_diagnosis, finalize_consultation, record_vitals, save_consultation
from .forms import ConsultationForm, DiagnosisForm, FinalizeConsultationForm, VitalSignForm
from .models import Diagnosis, MedicalRecord
from .worklists import encounter_worklist
from .reception import _audit


def _clinical_access(actor, visit):
    if visit.patient_id == actor.pk:
        return False, False
    return allowed(actor, "record.view", visit), allowed(actor, "vitals.record", visit)


@login_required
@require_http_methods(["GET"])
def worklist(request):
    actor = require_permission(request.user, "consultation.access")
    provider = clinical_provider(actor)
    finalized = request.GET.get("view") == "finalized" and provider.provider_type != Provider.Type.NURSE
    visits = encounter_worklist(provider, MedicalRecord.Status.FINALIZED if finalized else MedicalRecord.Status.DRAFT)
    return render(request, "clinical/consultation_list.html", {
        "page_obj": Paginator(visits, 10).get_page(request.GET.get("page")),
        "finalized": finalized, "nurse": provider.provider_type == Provider.Type.NURSE,
    })


def _history(actor, visit):
    history = MedicalRecord.objects.filter(
        patient=visit.patient, status=MedicalRecord.Status.FINALIZED, visited_at__lt=visit.visited_at,
    )
    if not patient_under_care(clinical_provider(actor), visit.patient):
        history = history.filter(provider_id=actor.pk)
    return history.order_by("-visited_at", "-pk")[:5]


def _submit(action, form, actor, visit):
    values = form.cleaned_data
    arguments = {"actor": actor, "record_id": visit.pk, "expected_version": values["expected_version"]}
    if action == "vitals":
        record_vitals(**arguments, measurements=values)
        return "Vital signs recorded."
    if action == "notes":
        primary = values["primary_diagnosis"]
        save_consultation(**arguments, notes=values, diagnosis_ids=[entry.pk for entry in values["diagnoses"]],
            primary_id=primary.pk if primary else None)
        return "Consultation draft saved."
    finalize_consultation(**arguments)
    return "Encounter finalized. The linked appointment, if any, is now Completed."


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def workspace(request, pk):
    actor = require_permission(request.user, "consultation.access")
    visit = get_object_or_404(MedicalRecord.objects.select_related("patient__patient", "provider__provider"), pk=pk)
    can_read_notes, can_record_vitals = _clinical_access(actor, visit)
    if not (can_read_notes or can_record_vitals):
        raise Http404
    can_edit = allowed(actor, "record.edit", visit)
    vitals = list(visit.vital_signs.select_related("recorded_by_user").order_by("-recorded_at", "-pk"))
    links = list(visit.diagnoses.select_related("diagnosis").order_by("-is_primary", "pk")) if can_read_notes else []
    latest_id = max((measurement.pk for measurement in vitals), default=None)
    version = consultation_version(visit, links if can_read_notes else visit.diagnoses.all(), latest_id)
    action = request.POST.get("action") if request.method == "POST" else None
    def data(form_action):
        return request.POST if form_action == action else None

    forms = {}
    if can_record_vitals:
        forms["vitals"] = VitalSignForm(data("vitals"), prefix="vitals", initial={"expected_version": version})
    if can_edit:
        primary = next((link.diagnosis_id for link in links if link.is_primary), None)
        initial = {field: getattr(visit, field) for field in NOTE_FIELDS}
        forms["notes"] = ConsultationForm(data("notes"), prefix="notes", initial={
            **initial, "expected_version": version, "diagnoses": [link.diagnosis_id for link in links], "primary_diagnosis": primary,
        })
        forms["finalize"] = FinalizeConsultationForm(data("finalize"), prefix="finalize", initial={"expected_version": version})
    if request.method == "POST":
        if action not in forms:
            raise PermissionDenied
        form = forms[action]
        if form.is_valid():
            try:
                message = _submit(action, form, actor, visit)
            except ValidationError as error:
                add_form_errors(form, error)
            else:
                messages.success(request, message)
                return redirect("consultation:workspace", pk=pk)
    response = render(request, "clinical/consultation.html", {
        "visit": visit, "vitals": vitals, "links": links, "can_read_notes": can_read_notes,
        "allergies": visit.patient.allergies.order_by("allergen", "pk"),
        "history": _history(actor, visit) if can_read_notes else (),
        "vitals_form": forms.get("vitals"), "notes_form": forms.get("notes"), "finalize_form": forms.get("finalize"),
    })
    if request.method == "GET":
        _audit(actor, "Clinical encounter viewed" if can_read_notes else "Clinical vitals viewed", visit)
    return response


@clinic_admin_required
@require_http_methods(["GET"])
def diagnosis_list(request):
    entries = Diagnosis.objects.order_by("coding_system", "code", "pk")
    return render(request, "clinical/diagnosis_list.html", {
        "page_obj": Paginator(entries, 10).get_page(request.GET.get("page")),
    })


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def diagnosis_create(request):
    form = DiagnosisForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            create_diagnosis(actor=request.user, **form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "This coding system and code are already in the catalog.")
        else:
            messages.success(request, "Diagnosis catalog entry added.")
            return redirect("consultation:diagnosis_list")
    return render(request, "includes/management_form.html", {
        "form": form, "title": "Add diagnosis catalog entry", "back_url": "consultation:diagnosis_list",
        "description": "Enter a supplied diagnosis code or a clearly fictional catalog entry for the demonstration.",
    })
