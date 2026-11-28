"""Portal actions for clinic setup."""
from datetime import date

from django.core.exceptions import ValidationError

from apps.appointments.services import save_room
from apps.billing.services import save_term
from apps.clinical.consultation import create_diagnosis
from apps.common.permissions import require_permission
from apps.prescriptions.services import save_medication
from apps.university.services import save_department


def save_reference(actor, data):
    require_permission(actor, "reference.manage")
    entry = data["entry"]
    row_id = data.get("id")
    table = data["table"]
    if table == "department":
        return save_department(actor=actor, department_id=row_id, **entry).pk
    if table == "clinic_room":
        return save_room(actor=actor, room_id=row_id, **entry).pk
    if table == "academic_term":
        entry = {**entry, "start_date": date.fromisoformat(entry["start_date"]), "end_date": date.fromisoformat(entry["end_date"])}
        return save_term(actor=actor, term_id=row_id, **entry).pk
    if table == "diagnosis" and row_id is None:
        return create_diagnosis(actor=actor, **entry)
    if table == "medication":
        return save_medication(actor=actor, medication_id=row_id, values=entry)
    raise ValidationError("Choose a supported reference catalog.")
