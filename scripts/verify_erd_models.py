"""Check every ERD column against Django metadata without opening the live DB."""
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_test"
import django
django.setup()
from django.apps import apps
from django.db import models

schema = runpy.run_path(str(ROOT / "docs/erd/generate_erd.py"))
schema["validate"]()
tables = schema["TABLES"]
actual = {m._meta.db_table: m for m in apps.get_models() if m._meta.db_table in tables}
assert set(actual) == set(tables)


def logical_type(field):
    if field.is_relation:
        return logical_type(field.target_field)
    if isinstance(field, models.CharField): return f"varchar({field.max_length})"
    if isinstance(field, models.TextField): return "text"
    if isinstance(field, models.BooleanField): return "boolean"
    if isinstance(field, models.DateTimeField): return "timestamptz"
    if isinstance(field, models.DateField): return "date"
    if isinstance(field, models.DecimalField): return f"numeric({field.max_digits},{field.decimal_places})"
    if isinstance(field, models.SmallIntegerField): return "smallint"
    if isinstance(field, (models.IntegerField, models.AutoField)): return "integer"
    raise AssertionError(f"Unmapped field: {field}")


for name, (_, rows) in tables.items():
    model = actual[name]
    fields = {f.column: f for f in model._meta.concrete_fields}
    assert set(fields) == {r[1] for r in rows}, f"Column mismatch: {name}"
    for key, column, field_type, nullability in rows:
        field = fields[column]
        assert logical_type(field) == field_type, f"Type mismatch: {name}.{column}"
        assert field.null == (nullability == "NULL"), f"Nullability mismatch: {name}.{column}"
        assert field.primary_key == ("PK" in key), f"Primary key mismatch: {name}.{column}"
        assert bool(field.is_relation) == ("FK" in key), f"FK mismatch: {name}.{column}"
        if "UQ" in key: assert field.unique, f"Unique mismatch: {name}.{column}"
    for group in schema["UNIQUE_GROUPS"].get(name, []):
        groups = {tuple(model._meta.get_field(f).column for f in c.fields) for c in model._meta.constraints if isinstance(c, models.UniqueConstraint) and c.condition is None}
        assert group in groups, f"Composite unique mismatch: {name}.{group}"
for child, col, parent, target_col, _ in schema["RELATIONS"]:
    field = next(f for f in actual[child]._meta.fields if f.column == col)
    assert field.related_model._meta.db_table == parent and field.target_field.column == target_col
print(f"PASS: all columns, types, nullability, primary/FK/unique keys, and {len(schema['RELATIONS'])} relationships match the {len(tables)}-entity ERD.")
