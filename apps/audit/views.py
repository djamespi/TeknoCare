from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from apps.common.permissions import require_permission
from apps.register.identity import identity_matches
from apps.register.models import User

from .forms import AuditFilterForm, ReportFilterForm
from .models import AuditLog
from .reports import filter_dates, operational_report


@login_required
@require_safe
@never_cache
def audit_list(request):
    require_permission(request.user, "audit.view")
    form = AuditFilterForm(request.GET)
    events = AuditLog.objects.order_by("-logged_at", "-pk").values(
        "pk", "action_performed", "target_table", "target_record_id", "logged_at",
        actor_id_text=F("actor_user__school_id"),
    )
    if form.is_valid():
        filters = form.cleaned_data
        events = filter_dates(events, "logged_at", filters)
        if actor := filters["actor"]:
            accounts = identity_matches(User.objects.all(), school_id=actor)
            events = events.filter(actor_user__in=accounts)
        if action := filters["action"]:
            events = events.filter(action_performed__icontains=action)
        if target_table := filters["target_table"]:
            events = events.filter(target_table=target_table)
        if filters["target_id"] is not None:
            events = events.filter(target_record_id=filters["target_id"])
    else:
        events = events.none()
    return render(request, "audit/history.html", {
        "filter_form": form, "page_obj": Paginator(events, 15).get_page(request.GET.get("page")),
    })


@login_required
@require_safe
@never_cache
def reports(request):
    require_permission(request.user, "reports.view")
    form = ReportFilterForm(request.GET)
    context = {"filter_form": form}
    if form.is_valid():
        report = operational_report(form.cleaned_data)
        context.update({
            "workload_page": Paginator(report.pop("workload"), 10).get_page(request.GET.get("workload_page")),
            "charges_page": Paginator(report.pop("charge_totals"), 10).get_page(request.GET.get("charges_page")),
            **report,
            "appointment_total": sum(count for _, count in report["appointment_counts"]),
            "visit_total": sum(count for _, count in report["visit_counts"]),
            "referral_total": sum(count for _, count in report["referral_counts"]),
        })
    return render(request, "audit/reports.html", context)
