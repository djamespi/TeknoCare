"""Patient-facing projection of the owning patient's finalized visits."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Prefetch
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.clinical.models import MedicalRecord, RecordDiagnosis, Referral
from apps.prescriptions.models import Prescription, PrescriptionItem

from .models import Patient


def _visits(request):
    patient = get_object_or_404(Patient, pk=request.user.pk)
    return MedicalRecord.objects.filter(patient=patient, status=MedicalRecord.Status.FINALIZED).values(
        "pk", "visited_at", "finalized_at", "appointment_id", "chief_complaint",
        attending_first=F("provider__provider__fname"), attending_last=F("provider__provider__lname"),
    )


def _referrals(record_id):
    return Referral.objects.filter(record_id=record_id).order_by("referred_at", "pk").values(
        "pk", "status", "referred_at", "destination", "reason",
        author_first=F("referred_by_provider__provider__fname"), author_last=F("referred_by_provider__provider__lname"),
    )


@login_required
@require_http_methods(["GET"])
@never_cache
def visit_list(request):
    visits = _visits(request).order_by("-visited_at", "-pk")
    return render(request, "patients/visits.html", {"page_obj": Paginator(visits, 10).get_page(request.GET.get("page"))})


@login_required
@require_http_methods(["GET"])
@never_cache
def visit_summary(request, pk, printing=False):
    visit = get_object_or_404(_visits(request), pk=pk)
    diagnoses = RecordDiagnosis.objects.filter(record_id=pk).order_by("-is_primary", "pk").values(
        "is_primary", description=F("diagnosis__description"),
    )
    items = PrescriptionItem.objects.select_related("medication").order_by("pk")
    prescriptions = Prescription.objects.filter(
        record_id=pk, status=Prescription.Status.ISSUED, issued_at__isnull=False,
    ).select_related("prescriber__provider").prefetch_related(
        Prefetch("items", queryset=items, to_attr="summary_items"),
    ).order_by("issued_at", "pk")
    return render(request, "patients/visit_summary.html", {
        "visit": visit, "diagnoses": diagnoses, "referrals": _referrals(pk), "prescriptions": prescriptions, "printing": printing,
    })


@login_required
@require_http_methods(["GET"])
@never_cache
def referral_print(request, pk, referral_id):
    visit = get_object_or_404(_visits(request), pk=pk)
    referral = get_object_or_404(_referrals(pk), pk=referral_id)
    return render(request, "patients/referral_print.html", {"visit": visit, "referral": referral})
