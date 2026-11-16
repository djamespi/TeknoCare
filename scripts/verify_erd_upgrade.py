"""Exercise a populated legacy upgrade in an isolated, in-memory SQLite DB.

Run with venv/Scripts/python.exe scripts/verify_erd_upgrade.py. This never uses
the configured database URL and is separate from the fresh-schema test suite.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
import django
django.setup()

from django.db import connection
from django.db.migrations.executor import MigrationExecutor

old_targets = [("register", "0001_initial"), ("profile", "0002_profile_age_profile_home_address"), ("user_settings", "0001_initial")]
executor = MigrationExecutor(connection)
executor.migrate(old_targets)
old = executor.loader.project_state(old_targets).apps
User = old.get_model("register", "User")
patient_user = User.objects.create(user_id=21, school_id="UPGRADE-STUDENT", fname="Fictional", lname="Patient", email="patient@example.invalid", password_hash="unusable-test-hash", user_type="Patient", account_status="Active")
doctor_user = User.objects.create(user_id=22, school_id="UPGRADE-DOCTOR", fname="Fictional", lname="Doctor", email="doctor@example.invalid", password_hash="unusable-test-hash", user_type="Provider", account_status="Active")
admin_user = User.objects.create(user_id=23, school_id="UPGRADE-ADMIN", fname="Fictional", lname="Admin", email="admin@example.invalid", password_hash="unusable-test-hash", user_type="Admin", account_status="Active")
patient = old.get_model("register", "Patient").objects.create(patient=patient_user, emergency_contact="Unstructured legacy contact", medical_history_summary="Fictional history", no_show_count=2)
provider = old.get_model("register", "Provider").objects.create(provider=doctor_user, specialization="Legacy specialty", room_number="OLD-101", is_active=True)
admin = old.get_model("register", "Admin").objects.create(admin=admin_user, access_level="Standard", department="Original department")
stamp = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
slot = old.get_model("register", "Slot").objects.create(provider=provider, start_time=stamp, end_time=stamp + timedelta(minutes=30), is_booked=True)
appointment = old.get_model("register", "Appointment").objects.create(patient=patient, provider=provider, slot=slot, reason_for_visit="Original reason", status="Completed")
record = old.get_model("register", "MedicalRecord").objects.create(appointment=appointment, patient=patient, provider=provider, symptoms="Original symptoms", diagnosis="Original free-text diagnosis", prescription_notes="Original prescription notes", created_at=stamp)
cancel_slot = old.get_model("register", "Slot").objects.create(provider=provider, start_time=stamp + timedelta(days=1), end_time=stamp + timedelta(days=1, minutes=30), is_booked=False)
cancel = old.get_model("register", "Appointment").objects.create(patient=patient, provider=provider, slot=cancel_slot, reason_for_visit="Old cancellation", status="Canceled")
old.get_model("register", "AuditLog").objects.create(admin=admin, action_performed="Legacy event", target_table="appointment", target_record_id=appointment.pk, logged_at=stamp)
old.get_model("register", "SupportTicket").objects.create(user=patient_user, admin=admin, request_type="Legacy support", description="Retain this historical ticket", status="Resolved")
old.get_model("profile", "Profile").objects.create(id=900, user=patient_user, full_name="Original profile display name", age=20, home_address="Original address", bio="Original bio")
old.get_model("user_settings", "UserSettings").objects.create(id=901, user=patient_user, dark_mode=True, email_notifications=False)

executor = MigrationExecutor(connection)
executor.migrate(executor.loader.graph.leaf_nodes())
from apps.patients.models import Patient
from apps.providers.models import Provider
from apps.appointments.models import Appointment, Slot
from apps.clinical.models import MedicalRecord
from apps.audit.models import AuditLog
from apps.profile.models import Profile
from apps.user_settings.models import UserSettings

assert Patient.objects.get(pk=21).affiliation is None
assert Provider.objects.get(pk=22).provider_type == "Unverified"
assert Slot.objects.get(pk=slot.pk).room_id is None
assert not Slot.objects.get(pk=slot.pk).is_active
assert Appointment.objects.get(pk=appointment.pk).provider.pk == 22
assert Appointment.objects.get(pk=cancel.pk).canceled_at is None
current = MedicalRecord.objects.get(pk=record.pk)
assert current.visited_at == stamp and current.symptoms == "Original symptoms"
assert current.affiliation_at_visit is None
assert AuditLog.objects.get().actor_user_id == 23
profile = Profile.objects.get(pk=21)
assert (profile.home_address, profile.bio) == ("Original address", "Original bio")
assert UserSettings.objects.get(pk=21).dark_mode
assert not UserSettings.objects.get(pk=21).email_notifications
with connection.cursor() as cursor:
    for query, expected in (
        ("SELECT emergency_contact, no_show_count FROM legacy_patient WHERE patient_id=21", ("Unstructured legacy contact", 2)),
        ("SELECT diagnosis, prescription_notes FROM legacy_medical_record", ("Original free-text diagnosis", "Original prescription notes")),
        ("SELECT id, full_name, age FROM legacy_profile_profile", (900, "Original profile display name", 20)),
        ("SELECT description FROM legacy_support_ticket", ("Retain this historical ticket",)),
        ("SELECT department FROM legacy_admin", ("Original department",)),
    ):
        cursor.execute(query)
        assert cursor.fetchone() == expected, query
print("PASS: populated legacy upgrade preserves IDs, account links, visit timestamps, profile/settings data, and audit actors.")
print("PASS: retired contact/history/admin/ticket data archived; unknown affiliation/room/designation remains unverified.")
print("SQLite only: PostgreSQL exclusion constraints and production upgrade still require staging verification.")
