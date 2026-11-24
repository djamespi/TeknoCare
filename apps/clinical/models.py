from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from apps.common.models import ValidatedModel
from apps.patients.models import Affiliation
from apps.providers.eligibility import provider_is_eligible


class MedicalRecord(ValidatedModel):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        FINALIZED = "Finalized", "Finalized"

    record_id = models.AutoField(primary_key=True)
    appointment = models.OneToOneField("appointments.Appointment", null=True, blank=True,
        related_name="medical_record", on_delete=models.PROTECT)
    patient = models.ForeignKey("patients.Patient", related_name="medical_records", on_delete=models.PROTECT)
    provider = models.ForeignKey("providers.Provider", related_name="medical_records", on_delete=models.PROTECT)
    chief_complaint = models.TextField(default="", blank=True)
    affiliation_at_visit = models.CharField(max_length=10, choices=Affiliation.choices, null=True, blank=True, editable=False)
    symptoms = models.TextField(null=True, blank=True)
    examination_notes = models.TextField(null=True, blank=True)
    treatment_plan = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    visited_at = models.DateTimeField(default=timezone.now)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "medical_record"
        indexes = [models.Index(fields=["patient", "visited_at"], name="record_patient_visited")]
        constraints = [
            models.CheckConstraint(check=models.Q(status__in=["Draft", "Finalized"]), name="record_status_valid"),
            models.CheckConstraint(check=models.Q(affiliation_at_visit__in=Affiliation.values) | models.Q(affiliation_at_visit__isnull=True), name="record_affiliation_valid"),
            models.CheckConstraint(check=models.Q(status="Draft", finalized_at__isnull=True) | models.Q(status="Finalized", finalized_at__isnull=False), name="record_finalization_time"),
            models.CheckConstraint(check=models.Q(finalized_at__isnull=True) | models.Q(finalized_at__gte=models.F("visited_at")), name="record_time_order"),
        ]

    def save(self, *args, **kwargs):
        if self._state.adding and self.patient_id:
            # Caller-supplied billing eligibility is never trusted for new visits.
            self.affiliation_at_visit = self.patient.affiliation
        return super().save(*args, **kwargs)

    def clean(self):
        if self._state.adding and not self.affiliation_at_visit:
            raise ValidationError("Verify patient affiliation before opening a visit.")
        if self._state.adding and self.provider_id and not provider_is_eligible(self.provider_id):
            raise ValidationError({"provider": "Verify and activate the attending provider."})
        if self.appointment_id:
            if self.appointment.patient_id != self.patient_id:
                raise ValidationError({"appointment": "The appointment belongs to another patient."})
            if self.appointment.status in ("Canceled", "No Show"):
                raise ValidationError("A canceled/no-show appointment cannot have a clinical encounter.")
        if self.status == self.Status.FINALIZED and not self.affiliation_at_visit:
            raise ValidationError("Review legacy visit affiliation before finalizing.")
        if self.status == self.Status.FINALIZED and not self.chief_complaint.strip():
            raise ValidationError({"chief_complaint": "Record the chief complaint before finalizing."})
        if self.pk and not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            if old.status == self.Status.FINALIZED:
                fields = [f.attname for f in self._meta.concrete_fields if not f.primary_key]
                if any(getattr(old, f) != getattr(self, f) for f in fields):
                    raise ValidationError("Finalized records require a controlled amendment, not an overwrite.")
            if old.affiliation_at_visit != self.affiliation_at_visit and self.student_charges.exists():
                raise ValidationError("Reconcile existing charges before changing visit eligibility.")
            if old.patient_id != self.patient_id and self.student_charges.exists():
                raise ValidationError("A charged encounter cannot be reassigned to another patient.")


class VitalSign(ValidatedModel):
    vital_id = models.AutoField(primary_key=True)
    record = models.ForeignKey(MedicalRecord, on_delete=models.PROTECT, related_name="vital_signs")
    recorded_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_vitals")
    recorded_at = models.DateTimeField(default=timezone.now, editable=False)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    systolic_mmhg = models.SmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    diastolic_mmhg = models.SmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    pulse_bpm = models.SmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    respiratory_rate = models.SmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    oxygen_saturation_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0.01"))])
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0.01"))])

    class Meta:
        db_table = "vital_sign"
        constraints = [
            models.CheckConstraint(check=(models.Q(systolic_mmhg__isnull=True, diastolic_mmhg__isnull=True) |
                models.Q(systolic_mmhg__isnull=False, diastolic_mmhg__isnull=False)), name="vitals_bp_pair"),
            models.CheckConstraint(check=models.Q(oxygen_saturation_pct__isnull=True) | models.Q(oxygen_saturation_pct__gte=0, oxygen_saturation_pct__lte=100), name="vitals_oxygen_range"),
            *[models.CheckConstraint(check=models.Q(**{f"{field}__isnull": True}) | models.Q(**{f"{field}__gt": 0}), name=f"vitals_{field}_positive")
              for field in ("systolic_mmhg", "diastolic_mmhg", "pulse_bpm", "respiratory_rate", "height_cm", "weight_kg")],
            models.CheckConstraint(check=(models.Q(temperature_c__isnull=False) | models.Q(systolic_mmhg__isnull=False) |
                models.Q(diastolic_mmhg__isnull=False) | models.Q(pulse_bpm__isnull=False) | models.Q(respiratory_rate__isnull=False) |
                models.Q(oxygen_saturation_pct__isnull=False) | models.Q(height_cm__isnull=False) | models.Q(weight_kg__isnull=False)), name="vitals_has_measurement"),
        ]


class Diagnosis(ValidatedModel):
    diagnosis_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20)
    description = models.CharField(max_length=255)
    coding_system = models.CharField(max_length=30)

    class Meta:
        db_table = "diagnosis"
        constraints = [models.UniqueConstraint(fields=["coding_system", "code"], name="unique_diagnosis_code")]

    def __str__(self):
        return f"{self.coding_system} {self.code} · {self.description}"


class RecordDiagnosis(ValidatedModel):
    # Django 4.2 cannot represent composite PKs; preserve pair uniqueness instead.
    record_diagnosis_id = models.AutoField(primary_key=True)
    record = models.ForeignKey(MedicalRecord, on_delete=models.PROTECT, related_name="diagnoses")
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.PROTECT, related_name="record_links")
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "record_diagnosis"
        constraints = [models.UniqueConstraint(fields=["record", "diagnosis"], name="unique_record_diagnosis"),
            models.UniqueConstraint(fields=["record"], condition=models.Q(is_primary=True), name="one_primary_diagnosis")]


class Referral(ValidatedModel):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"
        CANCELED = "Canceled", "Canceled"

    referral_id = models.AutoField(primary_key=True)
    record = models.ForeignKey(MedicalRecord, on_delete=models.PROTECT, related_name="referrals")
    referred_by_provider = models.ForeignKey("providers.Provider", on_delete=models.PROTECT, related_name="referrals")
    destination = models.CharField(max_length=200)
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    referred_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "referral"
        constraints = [models.CheckConstraint(check=models.Q(status__in=["Pending", "Completed", "Canceled"]), name="referral_status_valid")]

    def clean(self):
        if self._state.adding:
            if not (self.destination or "").strip() or not (self.reason or "").strip():
                raise ValidationError("Enter a referral destination and patient-facing reason or instructions.")
            if self.status != self.Status.PENDING or (self.record_id and self.record.status != MedicalRecord.Status.DRAFT):
                raise ValidationError("Create a Pending referral on a Draft encounter.")
            return
        previous = type(self).objects.get(pk=self.pk)
        content = ("record_id", "referred_by_provider_id", "destination", "reason", "referred_at")
        if any(getattr(previous, field) != getattr(self, field) for field in content):
            raise ValidationError("Referral content is immutable. Record a status change separately.")
        if self.status != previous.status and previous.status != self.Status.PENDING:
            raise ValidationError("Completed and canceled referrals cannot be reopened.")
