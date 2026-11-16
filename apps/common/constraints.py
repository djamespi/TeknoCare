"""PostgreSQL range constraints, skipped by SQLite's isolated test backend."""
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField
from django.db.models import Func


class TimestampRange(Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class PostgresExclusionConstraint(ExclusionConstraint):
    def constraint_sql(self, model, schema_editor):
        if schema_editor.connection.vendor == "postgresql":
            return super().constraint_sql(model, schema_editor)

    def create_sql(self, model, schema_editor):
        if schema_editor.connection.vendor == "postgresql":
            return super().create_sql(model, schema_editor)

    def remove_sql(self, model, schema_editor):
        if schema_editor.connection.vendor == "postgresql":
            return super().remove_sql(model, schema_editor)

    def validate(self, model, instance, exclude=None, using="default"):
        from django.db import connections
        if connections[using].vendor == "postgresql":
            return super().validate(model, instance, exclude, using)
