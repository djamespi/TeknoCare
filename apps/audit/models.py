from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.common.models import ValidatedModel


class AuditLog(ValidatedModel):
    log_id = models.AutoField(primary_key=True)
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="audit_events", null=True, blank=True, db_column="actor_user_id")
    action_performed = models.CharField(max_length=100)
    target_table = models.CharField(max_length=50)
    target_record_id = models.IntegerField()
    logged_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "audit_log"
        indexes = [models.Index(fields=["target_table", "target_record_id"], name="audit_target")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only.")
