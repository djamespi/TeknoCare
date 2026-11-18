from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.common.permissions import clinical_provider, require_permission
from apps.patients.models import Patient
from apps.providers.models import Provider


@login_required
def home_view(request):
    user = require_permission(request.user, "account.use")
    patient = Patient.objects.filter(pk=user.pk).first()
    provider = Provider.objects.filter(pk=user.pk).first() if user.user_type in {"Admin", "Provider"} else None
    return render(request, "home/home.html", {
        "patient": patient,
        "provider": provider,
        "provider_ready": bool(clinical_provider(user)) if provider else False,
    })
