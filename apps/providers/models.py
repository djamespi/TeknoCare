from django.conf import settings
from django.db import models
from apps.common.models import ValidatedModel


class Provider(ValidatedModel):
    class Type(models.TextChoices):
        PHYSICIAN = "Physician", "Physician"
        NURSE = "Nurse", "Nurse"
        DENTIST = "Dentist", "Dentist"
        UNVERIFIED = "Unverified", "Unverified legacy designation"

    provider = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True,
        db_column="provider_id", related_name="provider_profile", on_delete=models.PROTECT)
    provider_type = models.CharField(max_length=20, choices=Type.choices, default=Type.UNVERIFIED)
    license_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    specialization = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "provider"
        constraints = [models.CheckConstraint(check=models.Q(provider_type__in=["Physician", "Nurse", "Dentist", "Unverified"]), name="provider_type_valid")]

    def __str__(self):
        return str(self.provider)
