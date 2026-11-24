"""Referral follow-up updates status while preserving the original referral."""
from django.db import migrations


CONTENT = ("referral_id", "record_id", "referred_by_provider_id", "destination", "reason", "referred_at")
INSERT_GUARD = """NEW.status <> 'Pending' OR trim(NEW.destination) = '' OR trim(NEW.reason) = ''
    OR NOT EXISTS (
        SELECT 1 FROM medical_record visit JOIN provider clinician ON clinician.provider_id = visit.provider_id
        JOIN "user" account ON account.user_id = clinician.provider_id
        WHERE visit.record_id = NEW.record_id AND visit.status = 'Draft' AND visit.patient_id <> visit.provider_id
          AND clinician.provider_id = NEW.referred_by_provider_id AND clinician.is_active
          AND clinician.provider_type IN ('Physician', 'Dentist') AND account.account_status = 'Active'
          AND account.user_type IN ('Admin', 'Provider')
    )"""


def rules(vendor):
    operator = "IS DISTINCT FROM" if vendor == "postgresql" else "IS NOT"
    content_changed = " OR ".join(f"NEW.{field} {operator} OLD.{field}" for field in CONTENT)
    return (
        ("referral_open_pending", "INSERT", INSERT_GUARD, "Create a Pending referral on a Draft encounter with an eligible attending clinician"),
        ("referral_preserve_follow_up", "UPDATE", f"""({content_changed})
            OR (NEW.status {operator} OLD.status AND (OLD.status <> 'Pending' OR NEW.status NOT IN ('Completed', 'Canceled')))""",
            "Preserve referral content and follow up only a Pending referral"),
        ("referral_preserve_row", "DELETE", "1 = 1", "Cancel referrals to preserve their history"),
    )


def install(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor not in {"postgresql", "sqlite"}:
        raise RuntimeError("Referral guards require PostgreSQL or SQLite.")
    for name, event, predicate, message in rules(vendor):
        if vendor == "postgresql":
            returned = "OLD" if event == "DELETE" else "NEW"
            lock = "PERFORM record_id FROM medical_record WHERE record_id = NEW.record_id FOR SHARE;" if event == "INSERT" else ""
            schema_editor.execute(f"""
                CREATE FUNCTION {name}_fn() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    {lock}
                    IF {predicate} THEN RAISE EXCEPTION '{message}' USING ERRCODE = '23514'; END IF;
                    RETURN {returned};
                END; $$
            """)
            schema_editor.execute(f"""
                CREATE TRIGGER {name} BEFORE {event} ON referral
                FOR EACH ROW EXECUTE FUNCTION {name}_fn()
            """)
        else:
            schema_editor.execute(f"""
                CREATE TRIGGER {name} BEFORE {event} ON referral WHEN {predicate}
                BEGIN SELECT RAISE(ABORT, '{message}'); END
            """)


def remove(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    for name, _, _, _ in rules(vendor):
        if vendor == "postgresql":
            schema_editor.execute(f"DROP TRIGGER {name} ON referral")
            schema_editor.execute(f"DROP FUNCTION {name}_fn()")
        else:
            schema_editor.execute(f"DROP TRIGGER {name}")


class Migration(migrations.Migration):
    dependencies = [("clinical", "0005_protect_finalized_clinical_details")]
    operations = [migrations.RunPython(install, remove)]
