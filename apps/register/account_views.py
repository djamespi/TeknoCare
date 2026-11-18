from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.common.web import ReferenceFilterForm, add_form_errors, clinic_admin_required
from apps.patients.models import Patient
from .forms import AccountStatusForm, PersonnelAccountForm
from .models import User
from .services import create_personnel_account, set_account_status


@clinic_admin_required
@require_http_methods(["GET"])
def personnel_list(request):
    form = ReferenceFilterForm(request.GET)
    form.fields["state"].choices = [("", "All"), ("active", "Active"), ("inactive", "Suspended")]
    personnel = Patient.objects.select_related("patient", "department").filter(affiliation__in=["Faculty", "Staff"]).order_by("patient__school_id", "pk")
    if form.is_valid():
        query = form.cleaned_data["q"]
        personnel = personnel.filter(Q(patient__school_id__icontains=query) | Q(patient__fname__icontains=query) | Q(patient__lname__icontains=query))
        if form.cleaned_data["state"]:
            personnel = personnel.filter(patient__account_status="Active" if form.cleaned_data["state"] == "active" else "Suspended")
    else:
        personnel = personnel.none()
    return render(request, "register/personnel_list.html", {"filter_form": form,
        "page_obj": Paginator(personnel, 10).get_page(request.GET.get("page"))})


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def personnel_create(request):
    form = PersonnelAccountForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            create_personnel_account(actor=request.user, **form.account_values(), affiliation=form.cleaned_data["affiliation"], department=form.cleaned_data["department"])
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "That ID or email was just registered. Review the account list before retrying.")
        else:
            messages.success(request, "Personnel account created with a Patient profile. Share credentials privately and ask the person to change the password. No email was sent.")
            return redirect("accounts:personnel_list")
    return render(request, "includes/management_form.html", {"form": form, "title": "Add personnel account",
        "description": "Verify Faculty/Staff affiliation in person. Use fictional details for this prototype. Care is free for personnel; this creates no charge.", "back_url": "accounts:personnel_list"})


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def account_status(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.user_type == "Admin" or user.pk == request.user.pk:
        raise PermissionDenied("Admin account access requires trusted operator assistance.")
    form = AccountStatusForm(request.POST if request.method == "POST" else None, initial={"account_status": user.account_status})
    if request.method == "POST" and form.is_valid():
        try:
            set_account_status(actor=request.user, user_id=pk, status=form.cleaned_data["account_status"])
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            messages.success(request, "Account status saved. Suspension revokes sessions; reactivation does not restore old sessions. No history was deleted.")
            return redirect("university:management")
    return render(request, "includes/management_form.html", {"form": form, "title": "Change account access",
        "description": f"Account: {user.school_id} — {user.get_full_name()}. This does not change affiliation, role or clinical activation.", "back_url": "university:management"})
