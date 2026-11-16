from django.db import IntegrityError, transaction
from django.test import TestCase
from .models import AuditLog


class AuditHistoryTests(TestCase):
    def test_sql_updates_and_deletes_cannot_destroy_events(self):
        event = AuditLog.objects.create(action_performed="Test event", target_table="test", target_record_id=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AuditLog.objects.filter(pk=event.pk).update(action_performed="Changed")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AuditLog.objects.filter(pk=event.pk).delete()
