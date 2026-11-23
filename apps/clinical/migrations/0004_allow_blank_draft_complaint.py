from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clinical", "0003_diagnosis_recorddiagnosis_referral_vitalsign_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.AlterField(
                model_name="medicalrecord",
                name="chief_complaint",
                field=models.TextField(blank=True, default=""),
            ),
        ]),
    ]
