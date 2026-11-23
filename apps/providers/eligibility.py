def eligible_providers():
    from .models import Provider
    return Provider.objects.filter(is_active=True,
        provider_type__in=[Provider.Type.PHYSICIAN, Provider.Type.DENTIST, Provider.Type.NURSE],
        provider__account_status="Active", provider__user_type__in=["Admin", "Provider"])


def provider_is_eligible(provider_id):
    return eligible_providers().filter(pk=provider_id).exists()
