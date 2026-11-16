from django.conf import settings
from django.db import models


class UserSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.CASCADE, related_name="clinic_settings")
    dark_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)

    class Meta:
        db_table = "user_settings"

    def __str__(self):
        return f"Settings for {str(self.user) or self.user.get_username()}"
