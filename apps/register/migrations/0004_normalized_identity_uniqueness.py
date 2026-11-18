"""Reject ambiguous legacy identities before adding normalized unique indexes."""
from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def check_identity_collisions(apps, schema_editor):
    users = apps.get_model("register", "User").objects.using(schema_editor.connection.alias)
    for label, expression in (("university ID", Trim("school_id")), ("email", Lower(Trim("email")))):
        duplicates = users.annotate(identity_value=expression).values("identity_value").annotate(total=models.Count("pk")).filter(total__gt=1)
        if duplicates.exists():
            raise RuntimeError(f"Reconcile duplicate normalized {label} values before migrating; no identity values were rewritten.")


class Migration(migrations.Migration):
    dependencies = [("register", "0003_user_created_at_user_user_role_valid_and_more")]
    operations = [
        migrations.RunPython(check_identity_collisions, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="user", constraint=models.UniqueConstraint(Trim("school_id"), name="user_school_id_trim_unique"),
        ),
        migrations.AddConstraint(
            model_name="user", constraint=models.UniqueConstraint(Lower(Trim("email")), name="user_email_casefold_unique"),
        ),
    ]
