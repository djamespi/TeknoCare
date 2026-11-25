from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.common.permissions import clinical_provider, require_permission


@login_required
def home_view(request):
    user = require_permission(request.user, "account.use")
    patient = getattr(user, "patient_profile", None)
    provider = getattr(user, "provider_profile", None) if user.user_type in {"Admin", "Provider"} else None
    next_visit = None
    if patient and user.user_type == "Patient":
        next_visit = patient.appointments.filter(
            slot__start_time__gt=timezone.now(),
            status__in=(Appointment.Status.SCHEDULED, Appointment.Status.CHECKED_IN),
        ).select_related("slot__provider__provider", "slot__room").order_by("slot__start_time", "pk").first()
    return render(request, "home/home.html", {
        "patient": patient,
        "provider": provider,
        "provider_ready": bool(provider and clinical_provider(user)),
        "next_visit": next_visit,
        "today": timezone.localdate(),
    })
