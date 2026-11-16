"""Move model ownership without recreating clinical tables or losing old data."""
from django.db import migrations


def archive_retired_fields(apps, schema_editor):
    connection = schema_editor.connection
    quote = schema_editor.quote_name
    # Reject inconsistent provider history rather than silently dropping it.
    with connection.cursor() as cursor:
        cursor.execute('SELECT a.appointment_id FROM appointment a JOIN slot s ON a.slot_id = s.slot_id WHERE a.provider_id <> s.provider_id')
        if cursor.fetchone():
            raise RuntimeError("Reconcile appointment/slot provider mismatches before migrating.")
    # Immutable migration snapshots; not live feature tables. No credentials copied.
    for table in ("patient", "provider", "appointment", "medical_record", "profile_profile", "user_settings_usersettings"):
        schema_editor.execute(f"CREATE TABLE {quote('legacy_' + table)} AS SELECT * FROM {quote(table)}")


def protect_archives(apps, schema_editor):
    # CREATE TABLE AS does not inherit source policies. Archives are not API
    # tables: retain owner access without publicly exposing new snapshots.
    if schema_editor.connection.vendor == "postgresql":
        quote = schema_editor.quote_name
        for table in ("patient", "provider", "appointment", "medical_record", "profile_profile", "user_settings_usersettings", "admin", "support_ticket"):
            target = quote("legacy_" + table)
            schema_editor.execute(f"ALTER TABLE {target} ENABLE ROW LEVEL SECURITY")
            schema_editor.execute(f"REVOKE ALL ON TABLE {target} FROM PUBLIC")


class Migration(migrations.Migration):
    dependencies = [
        ("register", "0001_initial"),
        ("patients", "0001_adopt_existing_tables"),
        ("providers", "0001_adopt_existing_tables"),
        ("appointments", "0001_adopt_existing_tables"),
        ("clinical", "0001_adopt_existing_tables"),
        ("audit", "0002_user_actor"),
        ("profile", "0002_profile_age_profile_home_address"),
        ("user_settings", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(archive_retired_fields),
        migrations.AlterModelTable("supportticket", "legacy_support_ticket"),
        migrations.AlterModelTable("admin", "legacy_admin"),
        migrations.RunPython(protect_archives),
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.DeleteModel(name=name) for name in (
                "MedicalRecord", "Appointment", "Slot", "Patient", "Provider", "AuditLog", "SupportTicket", "Admin")
        ]),
    ]
