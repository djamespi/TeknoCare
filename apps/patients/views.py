from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.common.permissions import can, require_permission
from apps.common.web import add_form_errors
from apps.register.identity import identity_matches

from .forms import AllergyForm, BirthDateForm, EmergencyContactForm, UniversityIDForm
from .models import EmergencyContact, Patient
from .services import remove_emergency_contact, save_allergy, save_emergency_contact, update_birth_date


def _own_patient(request):
    user = require_permission(request.user, "account.use")
    return get_object_or_404(Patient, pk=user.pk)


@login_required
@require_http_methods(["GET"])
def patient_details(request):
    patient = _own_patient(request)
    return render(request, "patients/details.html", {
        "patient": patient,
        "contacts": patient.emergency_contacts.order_by("-is_primary", "full_name", "pk"),
        "allergies": patient.allergies.order_by("allergen", "pk"),
    })


@login_required
@require_http_methods(["GET", "POST"])
def birth_date(request):
    patient = _own_patient(request)
    form = BirthDateForm(request.POST if request.method == "POST" else None,
        initial={"date_of_birth": patient.date_of_birth})
    if request.method == "POST" and form.is_valid():
        try:
            update_birth_date(actor=request.user, **form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            messages.success(request, "Your birth date was saved.")
            return redirect("patients:details")
    return render(request, "patients/form.html", {
        "form": form, "title": "Edit birth date", "back_href": reverse("patients:details"),
    })


@login_required
@require_http_methods(["GET", "POST"])
def contact_edit(request, pk=None):
    patient = _own_patient(request)
    initial = {}
    if pk is not None:
        contact = get_object_or_404(patient.emergency_contacts, pk=pk)
        initial = {name: getattr(contact, name) for name in EmergencyContactForm.base_fields}
    form = EmergencyContactForm(request.POST if request.method == "POST" else None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            save_emergency_contact(actor=request.user, contact_id=pk, **form.cleaned_data)
        except EmergencyContact.DoesNotExist:
            raise Http404 from None
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            messages.success(request, "Emergency contact saved.")
            return redirect("patients:details")
    return render(request, "patients/form.html", {
        "form": form, "title": "Edit emergency contact" if pk is not None else "Add emergency contact",
        "back_href": reverse("patients:details"),
    })


@login_required
@require_http_methods(["GET", "POST"])
def contact_remove(request, pk):
    patient = _own_patient(request)
    contact = get_object_or_404(patient.emergency_contacts, pk=pk)
    if request.method == "POST":
        try:
            remove_emergency_contact(actor=request.user, contact_id=pk)
        except EmergencyContact.DoesNotExist:
            raise Http404 from None
        messages.success(request, "Emergency contact removed.")
        return redirect("patients:details")
    return render(request, "patients/contact_remove.html", {"contact": contact})


@login_required
@require_http_methods(["GET"])
def allergy_lookup(request):
    require_permission(request.user, "patient.allergy_lookup")
    form = UniversityIDForm(request.GET if request.GET else None)
    if form.is_valid():
        accounts = identity_matches(get_user_model().objects.all(), school_id=form.cleaned_data["school_id"])
        patient = Patient.objects.filter(patient__in=accounts).first()
        if patient and can(request.user, "patient.allergy_edit", patient):
            return redirect("patients:clinical_allergies", patient_id=patient.pk)
        form.add_error(None, "No patient is available for allergy review with that ID.")
    return render(request, "patients/allergy_lookup.html", {"form": form})


def _clinical_patient(request, patient_id):
    require_permission(request.user, "patient.allergy_lookup")
    patient = get_object_or_404(Patient.objects.select_related("patient"), pk=patient_id)
    if not can(request.user, "patient.allergy_edit", patient):
        raise Http404
    return patient


@login_required
@require_http_methods(["GET"])
def clinical_allergies(request, patient_id):
    patient = _clinical_patient(request, patient_id)
    return render(request, "patients/clinical_allergies.html", {
        "patient": patient, "allergies": patient.allergies.order_by("allergen", "pk"),
    })


@login_required
@require_http_methods(["GET", "POST"])
def allergy_edit(request, patient_id, pk=None):
    patient = _clinical_patient(request, patient_id)
    initial = {}
    if pk is not None:
        allergy = get_object_or_404(patient.allergies, pk=pk)
        initial = {name: getattr(allergy, name) for name in AllergyForm.base_fields}
    form = AllergyForm(request.POST if request.method == "POST" else None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            save_allergy(actor=request.user, patient_id=patient.pk, allergy_id=pk, **form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            messages.success(request, "Allergy saved.")
            return redirect("patients:clinical_allergies", patient_id=patient.pk)
    return render(request, "patients/form.html", {
        "form": form, "title": "Edit allergy" if pk is not None else "Record allergy",
        "description": f"Patient {patient.patient.get_full_name()} ({patient.patient.school_id})",
        "back_href": reverse("patients:clinical_allergies", args=[patient.pk]),
    })
