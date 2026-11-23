"""Protect finalized encounter details on PostgreSQL and SQLite."""
from django.db import migrations


CHILDREN = ("vital_sign", "record_diagnosis", "referral")
REFERRAL_CONTENT = (
    "referral_id", "record_id", "referred_by_provider_id", "destination", "reason", "referred_at",
)


def install_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        schema_editor.execute("""
            CREATE FUNCTION clinical_guard_final_child() RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE
                record_keys integer[] := '{}';
                parent_status text;
            BEGIN
                IF TG_OP <> 'INSERT' THEN record_keys := array_append(record_keys, OLD.record_id); END IF;
                IF TG_OP <> 'DELETE' THEN record_keys := array_append(record_keys, NEW.record_id); END IF;
                IF TG_TABLE_NAME = 'referral' AND TG_OP = 'UPDATE' THEN
                    IF (to_jsonb(OLD) - 'status') = (to_jsonb(NEW) - 'status') THEN RETURN NEW; END IF;
                END IF;
                FOR parent_status IN
                    SELECT status FROM medical_record WHERE record_id = ANY(record_keys)
                    ORDER BY record_id FOR SHARE
                LOOP
                    IF parent_status = 'Finalized' THEN
                        RAISE EXCEPTION 'Finalized encounter details are read-only' USING ERRCODE = '23514';
                    END IF;
                END LOOP;
                IF TG_TABLE_NAME = 'record_diagnosis' AND TG_OP <> 'DELETE' THEN
                    PERFORM diagnosis_id FROM diagnosis WHERE diagnosis_id = NEW.diagnosis_id FOR SHARE;
                END IF;
                IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
                RETURN NEW;
            END; $$
        """)
        for table in CHILDREN:
            schema_editor.execute(f"""
                CREATE TRIGGER clinical_keep_{table} BEFORE INSERT OR UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION clinical_guard_final_child()
            """)
        schema_editor.execute("""
            CREATE FUNCTION clinical_guard_final_record() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF OLD.status = 'Finalized' THEN
                    RAISE EXCEPTION 'Finalized encounters cannot be deleted' USING ERRCODE = '23514';
                END IF;
                RETURN OLD;
            END; $$
        """)
        schema_editor.execute("""
            CREATE TRIGGER clinical_keep_final_record BEFORE DELETE ON medical_record
            FOR EACH ROW EXECUTE FUNCTION clinical_guard_final_record()
        """)
        schema_editor.execute("""
            CREATE FUNCTION clinical_guard_catalog() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF EXISTS (SELECT 1 FROM record_diagnosis WHERE diagnosis_id = OLD.diagnosis_id) THEN
                    RAISE EXCEPTION 'A linked diagnosis catalog entry is immutable' USING ERRCODE = '23514';
                END IF;
                IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
                RETURN NEW;
            END; $$
        """)
        schema_editor.execute("""
            CREATE TRIGGER clinical_keep_catalog BEFORE UPDATE OR DELETE ON diagnosis
            FOR EACH ROW EXECUTE FUNCTION clinical_guard_catalog()
        """)
        return
    if vendor != "sqlite":
        raise RuntimeError("Clinical details guards require PostgreSQL or SQLite.")
    for table in CHILDREN:
        for operation, references in (("insert", ("NEW",)), ("update", ("OLD", "NEW")), ("delete", ("OLD",))):
            parent_ids = ", ".join(f"{reference}.record_id" for reference in references)
            condition = f"EXISTS (SELECT 1 FROM medical_record WHERE record_id IN ({parent_ids}) AND status = 'Finalized')"
            if table == "referral" and operation == "update":
                changed = " OR ".join(f"NEW.{field} IS NOT OLD.{field}" for field in REFERRAL_CONTENT)
                condition += f" AND ({changed})"
            schema_editor.execute(f"""
                CREATE TRIGGER clinical_keep_{table}_{operation} BEFORE {operation.upper()} ON {table}
                FOR EACH ROW WHEN {condition}
                BEGIN SELECT RAISE(ABORT, 'Finalized encounter details are read-only'); END
            """)
    schema_editor.execute("""
        CREATE TRIGGER clinical_keep_final_record BEFORE DELETE ON medical_record
        FOR EACH ROW WHEN OLD.status = 'Finalized'
        BEGIN SELECT RAISE(ABORT, 'Finalized encounters cannot be deleted'); END
    """)
    for operation in ("update", "delete"):
        schema_editor.execute(f"""
            CREATE TRIGGER clinical_keep_catalog_{operation} BEFORE {operation.upper()} ON diagnosis
            FOR EACH ROW WHEN EXISTS (SELECT 1 FROM record_diagnosis WHERE diagnosis_id = OLD.diagnosis_id)
            BEGIN SELECT RAISE(ABORT, 'A linked diagnosis catalog entry is immutable'); END
        """)


def remove_guards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        for table in CHILDREN:
            schema_editor.execute(f"DROP TRIGGER clinical_keep_{table} ON {table}")
        schema_editor.execute("DROP TRIGGER clinical_keep_final_record ON medical_record")
        schema_editor.execute("DROP TRIGGER clinical_keep_catalog ON diagnosis")
        for name in ("clinical_guard_final_child", "clinical_guard_final_record", "clinical_guard_catalog"):
            schema_editor.execute(f"DROP FUNCTION {name}()")
    else:
        for table in CHILDREN:
            for operation in ("insert", "update", "delete"):
                schema_editor.execute(f"DROP TRIGGER clinical_keep_{table}_{operation}")
        schema_editor.execute("DROP TRIGGER clinical_keep_final_record")
        for operation in ("update", "delete"):
            schema_editor.execute(f"DROP TRIGGER clinical_keep_catalog_{operation}")


class Migration(migrations.Migration):
    dependencies = [
        ("clinical", "0004_allow_blank_draft_complaint"),
        ("billing", "0002_protect_charge_history"),
    ]
    operations = [migrations.RunPython(install_guards, remove_guards)]
