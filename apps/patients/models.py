from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.common.models import ValidatedModel


class Affiliation(models.TextChoices):
    STUDENT = "Student", "Student"
    FACULTY = "Faculty", "Faculty"
    STAFF = "Staff", "Staff"


class Patient(ValidatedModel):
    patient = models.OneToOneField(settings.AUTH_USER_MODEL, primary_key=True,
        db_column="patient_id", related_name="patient_profile", on_delete=models.PROTECT)
    department = models.ForeignKey("university.Department", null=True, blank=True, on_delete=models.PROTECT)
    # NULL is intentionally reserved for unverified legacy data, never assumed billable.
    affiliation = models.CharField(max_length=10, choices=Affiliation.choices, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    medical_history_summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "patient"
        constraints = [models.CheckConstraint(
            check=models.Q(affiliation__in=Affiliation.values) | models.Q(affiliation__isnull=True),
            name="patient_affiliation_valid")]

    def clean(self):
        if self._state.adding and not self.affiliation:
            raise ValidationError({"affiliation": "Verify the patient's university affiliation."})
        if self.date_of_birth and self.date_of_birth > timezone.localdate():
            raise ValidationError({"date_of_birth": "Birth date cannot be in the future."})

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = timezone.localdate()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    def __str__(self):
        return str(self.patient)


class EmergencyContact(ValidatedModel):
    contact_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="emergency_contacts")
    full_name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=30)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "emergency_contact"
        constraints = [models.UniqueConstraint(fields=["patient"], condition=models.Q(is_primary=True), name="one_primary_contact")]


class PatientAllergy(ValidatedModel):
    class Severity(models.TextChoices):
        UNKNOWN = "Unknown", "Unknown"
        MILD = "Mild", "Mild"
        MODERATE = "Moderate", "Moderate"
        SEVERE = "Severe", "Severe"

    allergy_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="allergies")
    allergen = models.CharField(max_length=150)
    reaction = models.TextField(null=True, blank=True)
    severity = models.CharField(max_length=15, choices=Severity.choices, default=Severity.UNKNOWN)
    recorded_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "patient_allergy"
        constraints = [models.CheckConstraint(check=models.Q(severity__in=["Unknown", "Mild", "Moderate", "Severe"]), name="allergy_severity_valid")]
