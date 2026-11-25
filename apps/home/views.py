from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from apps.appointments.models import Appointment
from apps.audit.reports import reportable_appointments
from apps.clinical.models import MedicalRecord
from apps.clinical.worklists import encounter_worklist
from apps.common.permissions import clinical_provider, require_permission
from apps.portal.entrypoint import portal_ready


@login_required
@never_cache
def home_view(request):
    if portal_ready():
        return redirect("portal:index")
    user = require_permission(request.user, "account.use")
    today = timezone.localdate()
    patient = getattr(user, "patient_profile", None)
    provider = getattr(user, "provider_profile", None) if user.user_type in {"Admin", "Provider"} else None
    clinician = clinical_provider(user) if provider else None
    context = {
        "patient": patient, "provider": provider, "provider_ready": bool(clinician), "today": today,
    }

    if user.is_staff:
        totals = dict(reportable_appointments().filter(slot__start_time__date=today)
                      .values_list("status").annotate(total=Count("pk")))
        context["arrivals"] = [(label, totals.get(state, 0)) for state, label in Appointment.Status.choices]
    elif clinician:
        context["drafts"] = encounter_worklist(clinician, MedicalRecord.Status.DRAFT).values(
            "pk", "visited_at", "appointment_id",
        )[:4]
    elif patient and user.user_type == "Patient":
        context["next_visit"] = patient.appointments.filter(
            slot__start_time__gt=timezone.now(),
            status__in=(Appointment.Status.SCHEDULED, Appointment.Status.CHECKED_IN),
        ).select_related("slot__provider__provider", "slot__room").order_by("slot__start_time", "pk").first()
        context["recent_visits"] = patient.medical_records.filter(status=MedicalRecord.Status.FINALIZED).order_by(
            "-visited_at", "-pk",
        ).values("pk", "visited_at")[:3]
    return render(request, "home/home.html", context)
