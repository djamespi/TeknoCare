from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from apps.common.models import ValidatedModel


class Medication(ValidatedModel):
    medication_id = models.AutoField(primary_key=True)
    medication_code = models.CharField(max_length=30, unique=True)
    generic_name = models.CharField(max_length=150)
    strength = models.CharField(max_length=50)
    dosage_form = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "medication"

    def clean(self):
        if self.pk and not self._state.adding and self.items.filter(prescription__status="Issued").exists():
            old = type(self).objects.get(pk=self.pk)
            if any(getattr(old, f) != getattr(self, f) for f in ("generic_name", "strength", "dosage_form")):
                raise ValidationError("Create a new catalog entry to preserve issued prescription history.")


class Prescription(ValidatedModel):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        ISSUED = "Issued", "Issued"
        CANCELED = "Canceled", "Canceled"

    prescription_id = models.AutoField(primary_key=True)
    record = models.ForeignKey("clinical.MedicalRecord", on_delete=models.PROTECT, related_name="prescriptions")
    prescriber = models.ForeignKey("providers.Provider", on_delete=models.PROTECT, related_name="prescriptions")
    issued_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        db_table = "prescription"
        constraints = [models.CheckConstraint(check=models.Q(status__in=["Draft", "Issued", "Canceled"]), name="prescription_status_valid"),
            models.CheckConstraint(check=(models.Q(status="Draft", issued_at__isnull=True) | models.Q(status="Issued", issued_at__isnull=False) | models.Q(status="Canceled")), name="prescription_issue_time")]

    def clean(self):
        if self.status == self.Status.ISSUED and (not self.pk or not self.items.exists()):
            raise ValidationError("Add at least one medicine before issuing the prescription.")
        if self.pk and not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            if old.status == self.Status.CANCELED and self.status != old.status:
                raise ValidationError("Canceled prescriptions cannot be reissued.")
            if old.status == self.Status.ISSUED and (self.record_id != old.record_id or self.prescriber_id != old.prescriber_id or self.issued_at != old.issued_at or self.status == self.Status.DRAFT):
                raise ValidationError("Preserve issued prescriptions; cancel and replace them.")


class PrescriptionItem(ValidatedModel):
    item_id = models.AutoField(primary_key=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name="items")
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT, related_name="items")
    dose = models.CharField(max_length=100)
    route = models.CharField(max_length=50)
    frequency = models.CharField(max_length=100)
    duration_days = models.SmallIntegerField(validators=[MinValueValidator(1)])
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    quantity_unit = models.CharField(max_length=30)
    instructions = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "prescription_item"
        constraints = [models.CheckConstraint(check=models.Q(duration_days__gt=0, quantity__gt=0), name="prescription_item_positive")]

    def clean(self):
        if self.prescription_id and self.prescription.status != Prescription.Status.DRAFT:
            raise ValidationError("Only draft prescription items can be edited.")
        if self.pk and not self._state.adding:
            old = type(self).objects.select_related("prescription").get(pk=self.pk)
            if old.prescription.status != Prescription.Status.DRAFT:
                raise ValidationError("Issued prescription items cannot be moved or overwritten.")

    def delete(self, *args, **kwargs):
        if self.prescription.status != Prescription.Status.DRAFT:
            raise ValidationError("Issued prescription items cannot be deleted.")
        return super().delete(*args, **kwargs)
