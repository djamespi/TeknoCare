"""Keep original charge lines and distinguish voids from reversals."""
from django.db import migrations


ORIGINAL_FIELDS = ("charge_id", "record_id", "term_id", "description", "amount", "currency_code")


def install(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor not in {"postgresql", "sqlite"}:
        raise RuntimeError("Tuition charge guards require PostgreSQL or SQLite.")
    operator = "IS DISTINCT FROM" if vendor == "postgresql" else "IS NOT"
    changed = " OR ".join(f"NEW.{field} {operator} OLD.{field}" for field in ORIGINAL_FIELDS)
    predicate = f"""({changed}) OR (OLD.status = 'Pending' AND NEW.status = 'Voided'
        AND (NEW.posted_at IS NOT NULL OR NEW.billing_reference IS NOT NULL OR NEW.reversal_reference IS NOT NULL))"""
    if vendor == "postgresql":
        schema_editor.execute(f"""
            CREATE FUNCTION charge_preserve_original_fn() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF {predicate} THEN
                    RAISE EXCEPTION 'Preserve original charge details and lifecycle' USING ERRCODE = '23514';
                END IF;
                RETURN NEW;
            END; $$
        """)
        schema_editor.execute("""
            CREATE TRIGGER charge_preserve_original BEFORE UPDATE ON student_charge
            FOR EACH ROW EXECUTE FUNCTION charge_preserve_original_fn()
        """)
    else:
        schema_editor.execute(f"""
            CREATE TRIGGER charge_preserve_original BEFORE UPDATE ON student_charge WHEN {predicate}
            BEGIN SELECT RAISE(ABORT, 'Preserve original charge details and lifecycle'); END
        """)


def remove(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TRIGGER charge_preserve_original ON student_charge")
        schema_editor.execute("DROP FUNCTION charge_preserve_original_fn()")
    else:
        schema_editor.execute("DROP TRIGGER charge_preserve_original")


class Migration(migrations.Migration):
    dependencies = [("billing", "0002_protect_charge_history")]
    operations = [migrations.RunPython(install, remove)]
