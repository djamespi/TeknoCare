"""Cross-table safeguards cover SQL and bulk writes as well as model saves.

Frozen SQL deliberately lives in the migration, not current application models.
The PostgreSQL and SQLite versions implement the same row predicates.
"""
from django.db import migrations


def install_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor not in ("postgresql", "sqlite"):
        raise RuntimeError("Clinic data guards require PostgreSQL or SQLite.")
    different = lambda a, b: f"{a} IS DISTINCT FROM {b}" if vendor == "postgresql" else f"{a} IS NOT {b}"
    def changed(fields):
        return " OR ".join(different(f"NEW.{f}", f"OLD.{f}") for f in fields)

    # name, table, events, reject predicate, diagnostic.
    guards = [
        ("charge_student_only", "student_charge", "INSERT OR UPDATE",
         "COALESCE((SELECT affiliation_at_visit FROM medical_record WHERE record_id = NEW.record_id), '') <> 'Student'",
         "Only verified student visits can have tuition charges"),
        ("charge_new_pending", "student_charge", "INSERT", "NEW.status <> 'Pending'", "New charges must be Pending"),
        ("charge_new_term", "student_charge", "INSERT",
         "NOT EXISTS (SELECT 1 FROM academic_term WHERE term_id = NEW.term_id AND is_open_for_charges)", "Term is closed"),
        ("charge_creator", "student_charge", "INSERT",
         'NOT EXISTS (SELECT 1 FROM "user" WHERE user_id = NEW.created_by_user_id AND user_type = \'Admin\' AND account_status = \'Active\')', "Charge creation requires an active administrator"),
        ("charge_post_final", "student_charge", "UPDATE",
         "NEW.status = 'Posted' AND NOT EXISTS (SELECT 1 FROM medical_record WHERE record_id = NEW.record_id AND status = 'Finalized')", "Finalize the visit before posting charges"),
        ("charge_post_term", "student_charge", "UPDATE",
         "OLD.status = 'Pending' AND NEW.status = 'Posted' AND NOT EXISTS (SELECT 1 FROM academic_term WHERE term_id = NEW.term_id AND is_open_for_charges)", "Term is closed"),
        ("charge_identity", "student_charge", "UPDATE",
         changed(("charge_code", "created_at", "created_by_user_id")), "Charge identity is immutable"),
        ("charge_keep_posted", "student_charge", "UPDATE",
         "OLD.status = 'Posted' AND (NEW.status = 'Pending' OR " + changed(("record_id", "term_id", "description", "amount", "currency_code", "billing_reference", "posted_at")) + ")", "Reverse and replace posted charge details"),
        ("charge_keep_voided", "student_charge", "UPDATE", "OLD.status = 'Voided'", "Voided charges are immutable"),
        ("charge_no_delete", "student_charge", "DELETE", "1 = 1", "Void charges instead of deleting them"),
        ("visit_snapshot", "medical_record", "INSERT",
         different("NEW.affiliation_at_visit", "(SELECT affiliation FROM patient WHERE patient_id = NEW.patient_id)") + " OR NEW.affiliation_at_visit IS NULL", "Verify and snapshot patient affiliation"),
        ("visit_appointment", "medical_record", "INSERT OR UPDATE",
         "NEW.appointment_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM appointment WHERE appointment_id = NEW.appointment_id AND patient_id = NEW.patient_id AND status NOT IN ('Canceled', 'No Show'))", "Encounter must match an attended patient appointment"),
        ("visit_keep_billing", "medical_record", "UPDATE",
         "EXISTS (SELECT 1 FROM student_charge WHERE record_id = OLD.record_id) AND (" + changed(("patient_id", "affiliation_at_visit")) + ")", "Reconcile charges before changing visit identity"),
        ("visit_keep_final", "medical_record", "UPDATE",
         "OLD.status = 'Finalized' AND (" + changed(("appointment_id", "patient_id", "provider_id", "chief_complaint", "affiliation_at_visit", "symptoms", "examination_notes", "treatment_plan", "status", "visited_at", "finalized_at")) + ")", "Finalized encounters require controlled amendments"),
        ("user_keep_billing_id", '"user"', "UPDATE",
         different("NEW.school_id", "OLD.school_id") + " AND EXISTS (SELECT 1 FROM medical_record r JOIN student_charge c ON c.record_id = r.record_id WHERE r.patient_id = OLD.user_id)", "Reconcile tuition charges before changing university ID"),
        ("audit_no_delete", "audit_log", "DELETE", "1 = 1", "Audit events are append-only"),
        ("audit_no_edit", "audit_log", "UPDATE",
         changed(("action_performed", "target_table", "target_record_id", "logged_at")) + " OR (" + different("NEW.actor_user_id", "OLD.actor_user_id") + " AND NEW.actor_user_id IS NOT NULL)", "Audit events are append-only"),
    ]
    for name, table, events, predicate, message in guards:
        if vendor == "postgresql":
            returned = "OLD" if events == "DELETE" else "NEW"
            schema_editor.execute(f"""CREATE FUNCTION {name}_fn() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN IF {predicate} THEN RAISE EXCEPTION '{message}' USING ERRCODE = '23514'; END IF;
                RETURN {returned}; END; $$""")
            schema_editor.execute(f"CREATE TRIGGER {name} BEFORE {events} ON {table} FOR EACH ROW EXECUTE FUNCTION {name}_fn()")
        else:
            for event in events.split(" OR "):
                schema_editor.execute(f"CREATE TRIGGER {name}_{event.lower()} BEFORE {event} ON {table} FOR EACH ROW WHEN {predicate} BEGIN SELECT RAISE(ABORT, '{message}'); END")


def remove_guards(apps, schema_editor):
    tables = {
        "charge_student_only": "student_charge", "charge_new_pending": "student_charge", "charge_new_term": "student_charge",
        "charge_creator": "student_charge", "charge_post_final": "student_charge", "charge_post_term": "student_charge",
        "charge_identity": "student_charge", "charge_keep_posted": "student_charge", "charge_keep_voided": "student_charge", "charge_no_delete": "student_charge",
        "visit_snapshot": "medical_record", "visit_appointment": "medical_record", "visit_keep_billing": "medical_record", "visit_keep_final": "medical_record",
        "user_keep_billing_id": '"user"', "audit_no_delete": "audit_log", "audit_no_edit": "audit_log",
    }
    for name, table in tables.items():
        if schema_editor.connection.vendor == "postgresql":
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {name} ON {table}")
            schema_editor.execute(f"DROP FUNCTION IF EXISTS {name}_fn()")
        else:
            for event in ("insert", "update", "delete"):
                schema_editor.execute(f"DROP TRIGGER IF EXISTS {name}_{event}")


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
        ("audit", "0003_alter_auditlog_logged_at_auditlog_audit_target"),
        ("register", "0003_user_created_at_user_user_role_valid_and_more"),
        ("profile", "0003_remove_profile_age_remove_profile_full_name_and_more"),
        ("user_settings", "0002_remove_usersettings_id_alter_usersettings_user_and_more"),
        ("prescriptions", "0001_initial"),
    ]
    operations = [migrations.RunPython(install_guards, remove_guards)]
