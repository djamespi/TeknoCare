from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("clinical", "0001_adopt_existing_tables"), ("register", "0002_move_clinic_features")]
    operations = [migrations.RenameField("medicalrecord", "created_at", "visited_at")]
