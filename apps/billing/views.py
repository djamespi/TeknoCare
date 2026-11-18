from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.common.web import ReferenceFilterForm, add_form_errors, clinic_admin_required
from .forms import AcademicTermForm
from .models import AcademicTerm
from .services import save_term


@clinic_admin_required
@require_http_methods(["GET"])
def term_list(request):
    form = ReferenceFilterForm(request.GET)
    form.fields["state"].choices = [("", "All"), ("active", "Open"), ("inactive", "Closed")]
    terms = AcademicTerm.objects.order_by("-start_date", "-pk")
    if form.is_valid():
        query = form.cleaned_data["q"]
        terms = terms.filter(Q(academic_year__icontains=query) | Q(semester__icontains=query))
        if form.cleaned_data["state"]:
            terms = terms.filter(is_open_for_charges=form.cleaned_data["state"] == "active")
    else:
        terms = terms.none()
    return render(request, "billing/term_list.html", {"filter_form": form,
        "page_obj": Paginator(terms, 10).get_page(request.GET.get("page"))})


@clinic_admin_required
@require_http_methods(["GET", "POST"])
def term_edit(request, pk=None):
    term = get_object_or_404(AcademicTerm, pk=pk) if pk else None
    form = AcademicTermForm(request.POST if request.method == "POST" else None, instance=term)
    if request.method == "POST" and form.is_valid():
        try:
            save_term(actor=request.user, term_id=pk, **form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        except IntegrityError:
            form.add_error(None, "A conflicting academic term was saved. Review the year and semester.")
        else:
            messages.success(request, "Academic term saved. No tuition charges or payments were created.")
            return redirect("billing:term_list")
    return render(request, "includes/management_form.html", {"form": form, "title": "Edit academic term" if pk else "Add academic term",
        "description": "Closing a term preserves charges and allows later audited reversals. Referenced term identity and dates are protected.", "back_url": "billing:term_list"})
