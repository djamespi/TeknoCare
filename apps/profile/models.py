from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.CASCADE, related_name="clinic_profile")
    phone_number = models.CharField(max_length=30, null=True, blank=True)
    home_address = models.TextField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "user_profile"

    def __str__(self):
        return str(self.user) or self.user.get_username()
