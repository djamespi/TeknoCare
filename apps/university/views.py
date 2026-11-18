from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.common.web import ReferenceFilterForm, add_form_errors, clinic_admin_required
from .forms import DepartmentForm
from .models import Department
from .services import save_department


@clinic_admin_required
@require_http_methods(["GET"])
def management_home(request):
    return render(request, "university/management.html")


@clinic_admin_required
@require_http_methods(["GET"])
def department_list(request):
    form = ReferenceFilterForm(request.GET)
    departments = Department.objects.order_by("code", "pk")
    if form.is_valid():
        query = form.cleaned_data["q"]
        departments = departments.filter(Q(code__icontains=query) | Q(name__icontains=query))
        if form.cleaned_data["state"]:
            departments = departments.filter(is_active=form.cleaned_data["state"] == "active")
    else:
        departments = departments.none()
    return render(request, "university/department_list.html", {"filter_form": form,
        "page_obj": Paginator(departments, 10).get_page(request.GET.get("page"))})


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def department_edit(request, pk=None):
    department = get_object_or_404(Department, pk=pk) if pk else None
    form = DepartmentForm(request.POST if request.method == "POST" else None, instance=department)
    if request.method == "POST" and form.is_valid():
        try:
            save_department(actor=request.user, department_id=pk, **form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "A conflicting department was saved. Review the code and try again.")
        else:
            messages.success(request, "Department saved. Existing patient links were preserved.")
            return redirect("university:department_list")
    return render(request, "includes/management_form.html", {"form": form, "title": "Edit department" if pk else "Add department",
        "description": "Deactivate rather than delete. Existing patient affiliations are not changed.", "back_url": "university:department_list"})
