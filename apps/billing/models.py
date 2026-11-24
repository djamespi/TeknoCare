import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from apps.common.models import ValidatedModel


def charge_code():
    return uuid.uuid4().hex


class AcademicTerm(ValidatedModel):
    term_id = models.AutoField(primary_key=True)
    academic_year = models.CharField(max_length=9, validators=[RegexValidator(r"^\d{4}-\d{4}$", "Use YYYY-YYYY.")])
    semester = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    is_open_for_charges = models.BooleanField(default=False)

    class Meta:
        db_table = "academic_term"
        constraints = [models.UniqueConstraint(fields=["academic_year", "semester"], name="unique_academic_term"),
            models.CheckConstraint(check=models.Q(end_date__gte=models.F("start_date")), name="term_date_order")]

    def __str__(self):
        return f"{self.academic_year} · {self.semester}"

    def clean(self):
        if self.academic_year and len(self.academic_year) == 9:
            try:
                first, last = map(int, self.academic_year.split("-"))
                if last != first + 1:
                    raise ValueError
            except ValueError:
                raise ValidationError({"academic_year": "Academic years must be consecutive, e.g. 2026-2027."})


class StudentCharge(ValidatedModel):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        POSTED = "Posted", "Posted to tuition"
        VOIDED = "Voided", "Voided"

    charge_id = models.AutoField(primary_key=True)
    charge_code = models.CharField(max_length=40, unique=True, default=charge_code, editable=False)
    record = models.ForeignKey("clinical.MedicalRecord", on_delete=models.PROTECT, related_name="student_charges")
    term = models.ForeignKey(AcademicTerm, on_delete=models.PROTECT, related_name="student_charges")
    created_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_charges")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    currency_code = models.CharField(max_length=3, validators=[RegexValidator(r"^[A-Z]{3}$", "Use an uppercase three-letter currency.")])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    billing_reference = models.CharField(max_length=100, null=True, blank=True)
    reversal_reference = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    posted_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "student_charge"
        indexes = [models.Index(fields=["term", "status"], name="charge_term_status")]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="charge_positive_amount"),
            models.CheckConstraint(check=(
                models.Q(status="Pending", billing_reference__isnull=True, posted_at__isnull=True, reversal_reference__isnull=True, voided_at__isnull=True, void_reason__isnull=True) |
                (models.Q(status="Posted", billing_reference__isnull=False, posted_at__isnull=False, reversal_reference__isnull=True, voided_at__isnull=True, void_reason__isnull=True) & ~models.Q(billing_reference="")) |
                (models.Q(status="Voided", voided_at__isnull=False, void_reason__isnull=False) & ~models.Q(void_reason="") & (
                    models.Q(billing_reference__isnull=True, posted_at__isnull=True, reversal_reference__isnull=True) |
                    (models.Q(billing_reference__isnull=False, posted_at__isnull=False, reversal_reference__isnull=False) & ~models.Q(billing_reference="") & ~models.Q(reversal_reference=""))
                ))), name="charge_status_metadata"),
            models.CheckConstraint(check=models.Q(posted_at__isnull=True) | models.Q(posted_at__gte=models.F("created_at")), name="charge_post_time_order"),
            models.CheckConstraint(check=models.Q(voided_at__isnull=True) | (models.Q(voided_at__gte=models.F("created_at")) & (models.Q(posted_at__isnull=True) | models.Q(voided_at__gte=models.F("posted_at")))), name="charge_void_time_order"),
        ]

    def clean(self):
        if self._state.adding and self.created_by_user_id and (not self.created_by_user.is_active or not self.created_by_user.is_staff):
            raise ValidationError({"created_by_user": "An active administrator must create the charge."})
        if self.record_id and self.record.affiliation_at_visit != "Student":
            raise ValidationError({"record": "Only verified student visits may be charged. Personnel care is free."})
        if self._state.adding and self.status != self.Status.PENDING:
            raise ValidationError("Create a Pending charge before posting or voiding it.")
        if self.term_id and (self._state.adding or self.status == self.Status.POSTED) and not self.term.is_open_for_charges:
            # An already posted row may still be voided after the term closes.
            raise ValidationError({"term": "This term is closed for new postings."})
        if self.status == self.Status.POSTED and self.record.status != "Finalized":
            raise ValidationError("Finalize the encounter before posting its charges.")
        if self.currency_code != settings.CLINIC_CURRENCY_CODE:
            raise ValidationError({"currency_code": "Use the clinic's configured currency."})
        if self.pk and not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            if old.charge_code != self.charge_code or old.created_at != self.created_at or old.created_by_user_id != self.created_by_user_id:
                raise ValidationError("Charge identity and original creator are immutable.")
            if old.status == self.Status.VOIDED:
                raise ValidationError("Voided charges are immutable; create a corrected line.")
            line_fields = ("record_id", "term_id", "description", "amount", "currency_code")
            if any(getattr(old, field) != getattr(self, field) for field in line_fields):
                raise ValidationError("Preserve the original charge line. Void it and create a corrected line.")
            if old.status == self.Status.PENDING and self.status == self.Status.VOIDED and self.posted_at is not None:
                raise ValidationError("A Pending charge void cannot include posting or reversal metadata.")
            if old.status == self.Status.POSTED:
                immutable = ("billing_reference", "posted_at")
                if self.status == self.Status.PENDING or any(getattr(old, f) != getattr(self, f) for f in immutable):
                    raise ValidationError("Preserve posted charge details; reverse and replace the charge.")

    def delete(self, *args, **kwargs):
        raise ValidationError("Retain charge history; void charges instead of deleting them.")
