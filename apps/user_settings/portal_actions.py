"""Portal actions for the user settings feature."""
from apps.common.web import validated
from apps.user_settings.forms import UserSettingsForm
from apps.user_settings.models import UserSettings


def preferences(actor, data):
    instance, _ = UserSettings.objects.select_for_update().get_or_create(user=actor)
    form = UserSettingsForm({**{"dark_mode": instance.dark_mode, "email_notifications": instance.email_notifications},
                             **data}, instance=instance)
    validated(form)
    form.save()
