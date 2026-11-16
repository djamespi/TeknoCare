from django.db import models
from apps.common.models import ValidatedModel


class Department(ValidatedModel):
    department_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "department"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"
