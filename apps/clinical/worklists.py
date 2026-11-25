from django.db.models import Q
from django.utils import timezone

from apps.providers.models import Provider

from .models import MedicalRecord


def encounter_worklist(provider, status):
    scope = Q(provider=provider)
    if provider.provider_type == Provider.Type.NURSE:
        scope |= Q(visited_at__date=timezone.localdate())
    return MedicalRecord.objects.filter(scope, status=status).exclude(
        patient_id=provider.pk,
    ).select_related("patient__patient", "provider__provider").order_by("-visited_at", "-pk")
