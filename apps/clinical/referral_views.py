from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.common.permissions import allowed, require_permission
from apps.common.web import add_form_errors

from .forms import ReferralFollowUpForm, ReferralForm
from .models import MedicalRecord, Referral
from .referrals import create_referral, update_referral_status


def _clinical_visit(request, record_id, action=None):
    actor = require_permission(request.user, "consultation.access")
    visit = get_object_or_404(MedicalRecord.objects.select_related("patient__patient"), pk=record_id)
    if visit.patient_id == actor.pk or not allowed(actor, "record.view", visit):
        raise Http404
    if action and not allowed(actor, action, visit):
        raise PermissionDenied
    return actor, visit


@login_required
@require_http_methods(["GET"])
@never_cache
def referral_list(request, record_id):
    actor, visit = _clinical_visit(request, record_id)
    rows = visit.referrals.select_related("referred_by_provider__provider").order_by("-referred_at", "-pk")
    return render(request, "clinical/referrals.html", {
        "visit": visit, "page_obj": Paginator(rows, 10).get_page(request.GET.get("page")),
        "can_create": allowed(actor, "referral.create", visit), "can_follow_up": allowed(actor, "referral.follow_up", visit),
    })


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def referral_create(request, record_id):
    actor, visit = _clinical_visit(request, record_id, "referral.create")
    form = ReferralForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            create_referral(actor=actor, record_id=record_id, **form.cleaned_data)
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            messages.success(request, "Referral recorded.")
            return redirect("consultation:referrals", record_id=record_id)
    return render(request, "clinical/referral_form.html", {"visit": visit, "form": form})


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def referral_follow_up(request, record_id, pk):
    actor, visit = _clinical_visit(request, record_id, "referral.follow_up")
    referral = get_object_or_404(visit.referrals, pk=pk)
    form = ReferralFollowUpForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            update_referral_status(actor=actor, record_id=record_id, referral_id=pk, status=form.cleaned_data["status"])
        except ValidationError as error:
            add_form_errors(form, error)
        else:
            messages.success(request, "Referral follow-up saved.")
            return redirect("consultation:referrals", record_id=record_id)
    return render(request, "clinical/referral_form.html", {
        "visit": visit, "referral": referral, "form": form if referral.status == Referral.Status.PENDING or form.errors else None,
    })
