"""Enforce prescription lifecycle and immutable history at the database boundary."""
from django.db import migrations


IDENTITY = ("prescription_id", "record_id", "prescriber_id")
FORMULATION = ("medication_id", "medication_code", "generic_name", "strength", "dosage_form")
TEXT_FIELDS = ("dose", "route", "frequency", "quantity_unit")


def rules(vendor):
    operator = "IS DISTINCT FROM" if vendor == "postgresql" else "IS NOT"

    def changed(fields):
        return " OR ".join(f"NEW.{field} {operator} OLD.{field}" for field in fields)

    draft_visit = "EXISTS (SELECT 1 FROM medical_record WHERE record_id = NEW.record_id AND status = 'Draft')"
    eligible_prescriber = """EXISTS (
        SELECT 1 FROM medical_record visit JOIN provider practitioner ON practitioner.provider_id = visit.provider_id
        JOIN "user" account ON account.user_id = practitioner.provider_id
        WHERE visit.record_id = NEW.record_id AND practitioner.provider_id = NEW.prescriber_id
          AND visit.patient_id <> practitioner.provider_id AND practitioner.is_active
          AND practitioner.provider_type IN ('Physician', 'Dentist') AND account.account_status = 'Active'
          AND account.user_type IN ('Provider', 'Admin')
    )"""
    active_item = "EXISTS (SELECT 1 FROM medication WHERE medication_id = NEW.medication_id AND is_active)"
    blank = " OR ".join(f"trim(line.{field}) = ''" for field in TEXT_FIELDS)
    invalid_issue = f"""NOT EXISTS (SELECT 1 FROM prescription_item WHERE prescription_id = OLD.prescription_id)
        OR EXISTS (SELECT 1 FROM prescription_item line JOIN medication drug ON drug.medication_id = line.medication_id
        WHERE line.prescription_id = OLD.prescription_id AND (NOT drug.is_active OR {blank}))"""

    def editable_item(reference):
        return f"""EXISTS (SELECT 1 FROM prescription parent JOIN medical_record visit ON visit.record_id = parent.record_id
        WHERE parent.prescription_id = {reference}.prescription_id AND parent.status = 'Draft' AND visit.status = 'Draft')"""

    return (
        ("rx_create", "prescription", "INSERT", f"""NEW.status <> 'Draft' OR NOT ({draft_visit})
            OR NOT ({eligible_prescriber}) OR EXISTS (SELECT 1 FROM prescription
                WHERE record_id = NEW.record_id AND status = 'Draft')""",
            "Start one prescription draft per encounter with an eligible attending prescriber"),
        ("rx_update", "prescription", "UPDATE", f"""({changed(IDENTITY)}) OR OLD.status = 'Canceled'
            OR (OLD.status = 'Issued' AND (NEW.status = 'Draft' OR ({changed(('issued_at',))})))
            OR (OLD.status = 'Draft' AND (
                (NEW.status <> 'Canceled' AND NOT ({draft_visit}))
                OR (NEW.status = 'Canceled' AND NEW.issued_at IS NOT NULL)
                OR (NEW.status = 'Issued' AND (({invalid_issue}) OR NOT ({eligible_prescriber})))
            ))""", "Preserve prescription history and issue only valid items on a Draft encounter"),
        ("rx_delete", "prescription", "DELETE", "OLD.status <> 'Draft'",
            "Published and canceled prescriptions cannot be deleted"),
        ("rx_item_insert", "prescription_item", "INSERT", f"NOT ({editable_item('NEW')}) OR NOT ({active_item})",
            "Only active catalog items can be added to a Draft prescription"),
        ("rx_item_update", "prescription_item", "UPDATE", f"""({changed(('item_id', 'prescription_id'))})
            OR NOT ({editable_item('OLD')}) OR NOT ({active_item})""",
            "Prescription items cannot be moved or changed after issue or cancellation"),
        ("rx_item_delete", "prescription_item", "DELETE", f"NOT ({editable_item('OLD')})",
            "Published and canceled prescription items cannot be deleted"),
        ("rx_formulation", "medication", "UPDATE", f"""({changed(FORMULATION)}) AND EXISTS
            (SELECT 1 FROM prescription_item WHERE medication_id = OLD.medication_id)""",
            "Create a new medication entry to preserve referenced formulations"),
        ("rx_no_unresolved_draft", "medical_record", "UPDATE", """NEW.status = 'Finalized' AND OLD.status = 'Draft'
            AND EXISTS (SELECT 1 FROM prescription WHERE record_id = OLD.record_id AND status = 'Draft')""",
            "Resolve prescription drafts before finalizing"),
    )


def postgres_locks(name):
    if name == "rx_create":
        return "PERFORM record_id FROM medical_record WHERE record_id = NEW.record_id FOR UPDATE;"
    if name == "rx_update":
        return """
            PERFORM record_id FROM medical_record WHERE record_id = OLD.record_id FOR UPDATE;
            IF OLD.status = 'Draft' AND NEW.status = 'Issued' THEN
                PERFORM medication_id FROM medication
                    WHERE medication_id IN (SELECT medication_id FROM prescription_item
                        WHERE prescription_id = OLD.prescription_id)
                    ORDER BY medication_id FOR SHARE;
            END IF;
        """
    if name.startswith("rx_item_"):
        reference = "NEW" if name == "rx_item_insert" else "OLD"
        statements = f"PERFORM prescription_id FROM prescription WHERE prescription_id = {reference}.prescription_id FOR UPDATE;"
        if name != "rx_item_delete":
            statements += " PERFORM medication_id FROM medication WHERE medication_id = NEW.medication_id FOR SHARE;"
        return statements
    return ""


def install(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor not in {"postgresql", "sqlite"}:
        raise RuntimeError("Prescription guards require PostgreSQL or SQLite.")
    for name, table, event, predicate, message in rules(vendor):
        if vendor == "postgresql":
            returned = "OLD" if event == "DELETE" else "NEW"
            schema_editor.execute(f"""
                CREATE FUNCTION {name}_fn() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    {postgres_locks(name)}
                    IF {predicate} THEN RAISE EXCEPTION '{message}' USING ERRCODE = '23514'; END IF;
                    RETURN {returned};
                END; $$
            """)
            schema_editor.execute(f"""
                CREATE TRIGGER {name} BEFORE {event} ON {table}
                FOR EACH ROW EXECUTE FUNCTION {name}_fn()
            """)
        else:
            schema_editor.execute(f"""
                CREATE TRIGGER {name} BEFORE {event} ON {table} FOR EACH ROW WHEN {predicate}
                BEGIN SELECT RAISE(ABORT, '{message}'); END
            """)


def remove(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    for name, table, _, _, _ in rules(vendor):
        if vendor == "postgresql":
            schema_editor.execute(f"DROP TRIGGER {name} ON {table}")
            schema_editor.execute(f"DROP FUNCTION {name}_fn()")
        else:
            schema_editor.execute(f"DROP TRIGGER {name}")


class Migration(migrations.Migration):
    dependencies = [
        ("prescriptions", "0001_initial"),
        ("clinical", "0005_protect_finalized_clinical_details"),
    ]
    operations = [migrations.RunPython(install, remove)]
