from django.contrib.postgres.fields import RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.common.constraints import PostgresExclusionConstraint, TimestampRange
from apps.common.models import ValidatedModel
from apps.providers.eligibility import provider_is_eligible


class ClinicRoom(ValidatedModel):
    room_id = models.AutoField(primary_key=True)
    campus = models.CharField(max_length=100)
    building = models.CharField(max_length=100)
    room_number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "clinic_room"
        constraints = [models.UniqueConstraint(fields=["campus", "building", "room_number"], name="unique_clinic_room")]


class Slot(ValidatedModel):
    slot_id = models.AutoField(primary_key=True)
    provider = models.ForeignKey("providers.Provider", on_delete=models.PROTECT, related_name="slots")
    # Legacy slots remain NULL/inactive until their room is verified.
    room = models.ForeignKey(ClinicRoom, on_delete=models.PROTECT, null=True, blank=True, related_name="slots")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "slot"
        indexes = [models.Index(fields=["provider", "start_time"], name="slot_provider_start")]
        constraints = [
            models.CheckConstraint(check=models.Q(end_time__gt=models.F("start_time")), name="slot_positive_duration"),
            models.CheckConstraint(check=models.Q(is_active=False) | models.Q(room__isnull=False), name="active_slot_has_room"),
            *[PostgresExclusionConstraint(name=f"slot_no_{field}_overlap", condition=models.Q(is_active=True),
                expressions=[(field, RangeOperators.EQUAL), (TimestampRange("start_time", "end_time", models.Value("[)")), RangeOperators.OVERLAPS)])
              for field in ("provider", "room")],
        ]

    @property
    def is_booked(self):
        return self.appointments.exclude(status=Appointment.Status.CANCELED).exists() if self.pk else False

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "Slot must end after it starts."})
        if self.is_active:
            if not self.room_id or not ClinicRoom.objects.filter(pk=self.room_id, is_active=True).exists():
                raise ValidationError({"room": "Active availability needs an active, verified room."})
            if not provider_is_eligible(self.provider_id):
                raise ValidationError({"provider": "Verify and activate this provider before scheduling."})
            overlap = type(self).objects.filter(is_active=True, start_time__lt=self.end_time, end_time__gt=self.start_time).exclude(pk=self.pk)
            if overlap.filter(models.Q(provider_id=self.provider_id) | models.Q(room_id=self.room_id)).exists():
                raise ValidationError("The provider or room already has overlapping availability.")
        if self.pk and not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            changed = any(getattr(old, f) != getattr(self, f) for f in ("provider_id", "start_time", "end_time", "room_id"))
            if changed and self.appointments.exclude(status=Appointment.Status.CANCELED).exists():
                raise ValidationError("Cancel existing bookings before changing a slot.")


class Appointment(ValidatedModel):
    class Status(models.TextChoices):
        SCHEDULED = "Scheduled", "Scheduled"
        CHECKED_IN = "Checked-In", "Checked in"
        COMPLETED = "Completed", "Completed"
        CANCELED = "Canceled", "Canceled"
        NO_SHOW = "No Show", "No show"

    appointment_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="appointments")
    slot = models.ForeignKey(Slot, on_delete=models.PROTECT, related_name="appointments")
    reason_for_visit = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "appointment"
        indexes = [models.Index(fields=["patient", "status"], name="appointment_patient_status")]
        constraints = [
            models.UniqueConstraint(fields=["slot"], condition=~models.Q(status="Canceled"), name="one_live_booking_per_slot"),
            models.CheckConstraint(check=models.Q(status__in=["Scheduled", "Checked-In", "Completed", "Canceled", "No Show"]), name="appointment_status_valid"),
            # Historical cancellations have no trustworthy timestamp. New saves
            # require it in clean(); preserve unknown legacy values in the DB.
            models.CheckConstraint(check=models.Q(status="Canceled") | models.Q(canceled_at__isnull=True), name="appointment_cancel_time"),
        ]

    @property
    def provider(self):
        return self.slot.provider

    def clean(self):
        if self.status == self.Status.CANCELED and not self.canceled_at:
            raise ValidationError({"canceled_at": "Record the cancellation time."})
        if self._state.adding and self.status != self.Status.CANCELED and not self.slot.is_active:
            raise ValidationError({"slot": "Choose active availability."})
        if self.patient_id and self.slot_id and self.status in (self.Status.SCHEDULED, self.Status.CHECKED_IN):
            if type(self).objects.filter(patient_id=self.patient_id, status__in=[self.Status.SCHEDULED, self.Status.CHECKED_IN],
                slot__start_time__lt=self.slot.end_time, slot__end_time__gt=self.slot.start_time).exclude(pk=self.pk).exists():
                raise ValidationError("This patient already has an overlapping appointment.")
        if self.pk and not self._state.adding and hasattr(self, "medical_record"):
            old = type(self).objects.get(pk=self.pk)
            if old.patient_id != self.patient_id or old.slot_id != self.slot_id or self.status in (self.Status.CANCELED, self.Status.NO_SHOW):
                raise ValidationError("Preserve bookings linked to clinical records.")
