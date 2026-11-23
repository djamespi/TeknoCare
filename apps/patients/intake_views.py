from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.common.web import add_form_errors, clinic_admin_required
from apps.register.identity import identity_matches
from apps.register.models import User
from apps.register.services import add_patient_profile, correct_patient_identity, create_patient_account

from .forms import AffiliationForm, AttachPatientForm, NewPatientAccountForm, PatientFilterForm, PatientIdentityForm, UniversityIDForm
from .models import Patient
from .services import update_affiliation


@clinic_admin_required
@require_http_methods(["GET"])
def patient_list(request):
    form = PatientFilterForm(request.GET)
    patients = Patient.objects.select_related("patient", "department").order_by("patient__school_id", "pk")
    if form.is_valid():
        query = form.cleaned_data["q"]
        if query:
            patients = patients.alias(display_name=Concat("patient__fname", Value(" "), "patient__lname")).filter(
                Q(patient__school_id__icontains=query) | Q(display_name__icontains=query)
            )
        affiliation = form.cleaned_data["affiliation"]
        if affiliation:
            patients = patients.filter(affiliation=None if affiliation == "unknown" else affiliation)
    else:
        patients = patients.none()
    return render(request, "patients/intake_list.html", {
        "filter_form": form, "page_obj": Paginator(patients, 10).get_page(request.GET.get("page")),
    })


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def patient_create(request):
    form = NewPatientAccountForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            create_patient_account(actor=request.user, **form.account_values(), **form.affiliation_values(),
                date_of_birth=form.cleaned_data["date_of_birth"])
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "That ID or email was just registered. Review the patient list before retrying.")
        else:
            messages.success(request, "Patient account created. Share the initial password privately. No email was sent.")
            return redirect("patient_intake:list")
    return render(request, "patients/form.html", {
        "form": form, "title": "Create patient account", "back_href": reverse("patient_intake:list"),
        "description": "Use fictional details and confirm the patient's affiliation before creating their login.",
    })


@clinic_admin_required
@require_http_methods(["GET"])
def account_lookup(request):
    form = UniversityIDForm(request.GET if request.GET else None)
    account = None
    if form.is_valid():
        account = identity_matches(User.objects.select_related("patient_profile"), school_id=form.cleaned_data["school_id"]).first()
        if account is None:
            form.add_error(None, "No account matches that University ID.")
    return render(request, "patients/account_lookup.html", {"form": form, "account": account})


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def patient_attach(request, pk):
    account = get_object_or_404(User, pk=pk)
    if hasattr(account, "patient_profile"):
        messages.info(request, "This account already has a patient profile.")
        return redirect("patient_intake:affiliation", pk=pk)
    form = AttachPatientForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            add_patient_profile(actor=request.user, user_id=pk, **form.affiliation_values(),
                date_of_birth=form.cleaned_data["date_of_birth"])
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            messages.success(request, "Patient profile added. The account keeps its existing login and role.")
            return redirect("patient_intake:list")
    return render(request, "patients/form.html", {
        "form": form, "title": "Add patient profile", "back_href": reverse("patient_intake:account_lookup"),
        "description": f"Account {account.get_full_name()} ({account.school_id})",
    })


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def affiliation_edit(request, pk):
    patient = get_object_or_404(Patient.objects.select_related("patient"), pk=pk)
    form = AffiliationForm(request.POST if request.method == "POST" else None, patient=patient,
        initial={"affiliation": patient.affiliation, "department": patient.department_id})
    if request.method == "POST" and form.is_valid():
        try:
            update_affiliation(actor=request.user, patient_id=pk, **form.affiliation_values())
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            messages.success(request, "Patient affiliation details saved. Past visit affiliations are preserved.")
            return redirect("patient_intake:list")
    return render(request, "patients/form.html", {
        "form": form, "title": "Correct patient affiliation", "back_href": reverse("patient_intake:list"),
        "description": f"Patient {patient.patient.get_full_name()} ({patient.patient.school_id})",
    })


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def identity_edit(request, pk):
    account = get_object_or_404(Patient.objects.select_related("patient"), pk=pk).patient
    form = PatientIdentityForm(request.POST if request.method == "POST" else None, initial={
        "school_id": account.school_id, "first_name": account.fname, "last_name": account.lname, "email": account.email,
    })
    if request.method == "POST" and form.is_valid():
        values = {field: form.cleaned_data[field] for field in ("school_id", "email", "first_name", "last_name")}
        try:
            correct_patient_identity(actor=request.user, user_id=pk, **values)
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "That ID or email is already registered. Review the account before retrying.")
        else:
            messages.success(request, "Account identity saved. Use the corrected University ID for future sign-ins.")
            return redirect("patient_intake:list")
    return render(request, "patients/form.html", {
        "form": form, "title": "Correct account identity", "back_href": reverse("patient_intake:list"),
        "description": "Confirm the corrected details with the account holder. The University ID is their sign-in ID.",
    })
