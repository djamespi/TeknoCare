"""Portal actions for the providers feature."""
from apps.common.permissions import require_permission
from apps.common.web import validated
from apps.providers.forms import ProviderAccountForm
from apps.register.services import create_provider_account


def add_provider(actor, data):
    require_permission(actor, "accounts.manage")
    form = ProviderAccountForm(data)
    values = validated(form)
    return create_provider_account(
        actor=actor, **form.account_values(), provider_type=values["provider_type"],
        license_number=values["license_number"], specialization=values["specialization"] or None,
    ).pk
