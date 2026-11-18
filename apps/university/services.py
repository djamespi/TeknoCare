from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditLog
from apps.common.permissions import require_permission
from apps.patients.models import Patient
from .models import Department


@transaction.atomic
def save_department(*, actor, code, name, is_active, department_id=None):
    actor = require_permission(actor, "reference.manage")
    department = Department.objects.select_for_update().get(pk=department_id) if department_id else Department()
    code = code.strip()
    if department_id and department.code != code and Patient.objects.filter(department_id=department_id).exists():
        raise ValidationError({"code": "Keep the referenced department code; create a new department for a different identity."})
    department.code, department.name, department.is_active = code, name.strip(), is_active
    department.save()
    AuditLog.objects.create(actor_user=actor, action_performed="Department updated" if department_id else "Department created",
        target_table="department", target_record_id=department.pk)
    return department
