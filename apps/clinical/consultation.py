"""Authorized, transactional consultation writes."""
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.appointments.models import Appointment
from apps.common.permissions import require_permission

from .models import Diagnosis, MedicalRecord, RecordDiagnosis, VitalSign
from .reception import _audit, lock_encounter_for_update


NOTE_FIELDS = ("chief_complaint", "symptoms", "examination_notes", "treatment_plan")
VITAL_FIELDS = (
    "temperature_c", "systolic_mmhg", "diastolic_mmhg", "pulse_bpm",
    "respiratory_rate", "oxygen_saturation_pct", "height_cm", "weight_kg",
)


def consultation_version(visit, links, latest_vital_id):
    values = [
        visit.pk, visit.patient_id, visit.provider_id, visit.appointment_id, visit.status,
        visit.affiliation_at_visit, *(getattr(visit, field) for field in NOTE_FIELDS),
        sorted((link.pk, link.diagnosis_id, link.is_primary, link.notes) for link in links),
        latest_vital_id,
    ]
    return salted_hmac("clinical.consultation", json.dumps(values), algorithm="sha256").hexdigest()


def _locked_draft(actor, record_id, action):
    user = require_permission(actor, "consultation.access")
    snapshot = MedicalRecord.objects.get(pk=record_id)
    require_permission(user, action, snapshot)
    visit = lock_encounter_for_update(snapshot, actor_id=user.pk)
    user = require_permission(user, action, visit)
    if visit.appointment_id and visit.appointment.status != Appointment.Status.CHECKED_IN:
        raise ValidationError("A linked appointment must be Checked in before documenting care.")
    return user, visit


def _check_version(visit, expected_version, links):
    latest_vital_id = visit.vital_signs.aggregate(latest=Max("pk"))["latest"]
    current = consultation_version(visit, links, latest_vital_id)
    if not constant_time_compare(current, expected_version or ""):
        raise ValidationError("This encounter changed. Reload it and review the current details before submitting again.")


@transaction.atomic
def record_vitals(*, actor, record_id, expected_version, measurements):
    user, visit = _locked_draft(actor, record_id, "vitals.record")
    _check_version(visit, expected_version, visit.diagnoses.all())
    vital = VitalSign.objects.create(
        record=visit, recorded_by_user=user,
        **{field: measurements.get(field) for field in VITAL_FIELDS},
    )
    _audit(user, "Vital signs recorded", vital)


@transaction.atomic
def save_consultation(*, actor, record_id, expected_version, notes, diagnosis_ids, primary_id=None):
    user, visit = _locked_draft(actor, record_id, "record.edit")
    links = list(visit.diagnoses.all())
    _check_version(visit, expected_version, links)
    selected = set(diagnosis_ids)
    if len(selected) != len(diagnosis_ids) or Diagnosis.objects.filter(pk__in=selected).count() != len(selected):
        raise ValidationError({"diagnoses": "Choose distinct entries from the diagnosis catalog."})
    if primary_id is not None and primary_id not in selected:
        raise ValidationError({"primary_diagnosis": "Select the primary diagnosis in the diagnoses list too."})

    for field in NOTE_FIELDS:
        value = (notes.get(field) or "").strip()
        setattr(visit, field, value if field == "chief_complaint" else value or None)
    visit.save(update_fields=NOTE_FIELDS)
    existing = {link.diagnosis_id: link for link in links}
    visit.diagnoses.exclude(diagnosis_id__in=selected).delete()
    visit.diagnoses.filter(is_primary=True).exclude(diagnosis_id=primary_id).update(is_primary=False)
    for diagnosis_id in sorted(selected):
        if diagnosis_id not in existing:
            RecordDiagnosis.objects.create(record=visit, diagnosis_id=diagnosis_id, is_primary=diagnosis_id == primary_id)
    if primary_id in existing:
        visit.diagnoses.filter(diagnosis_id=primary_id, is_primary=False).update(is_primary=True)
    _audit(user, "Consultation draft saved", visit)


@transaction.atomic
def finalize_consultation(*, actor, record_id, expected_version):
    user, visit = _locked_draft(actor, record_id, "record.finalize")
    _check_version(visit, expected_version, visit.diagnoses.all())
    if visit.prescriptions.filter(status="Draft").exists():
        raise ValidationError("Issue or discard every prescription draft before finalizing the encounter.")
    if not visit.chief_complaint.strip():
        raise ValidationError("Record the chief complaint before finalizing.")
    if not any((getattr(visit, field) or "").strip() for field in ("symptoms", "examination_notes")):
        raise ValidationError("Record symptoms or examination notes before finalizing.")
    if not (visit.treatment_plan or "").strip():
        raise ValidationError("Record the treatment plan before finalizing.")
    visit.status = MedicalRecord.Status.FINALIZED
    visit.finalized_at = timezone.now()
    visit.save(update_fields=["status", "finalized_at"])
    _audit(user, "Consultation finalized", visit)
    if visit.appointment_id:
        appointment = visit.appointment
        Appointment.objects.filter(pk=appointment.pk).update(status=Appointment.Status.COMPLETED)
        _audit(user, "Appointment completed by finalization", appointment)


@transaction.atomic
def create_diagnosis(*, actor, coding_system, code, description):
    user = require_permission(actor, "reference.manage")
    diagnosis = Diagnosis.objects.create(
        coding_system=coding_system.strip(), code=code.strip(), description=description.strip(),
    )
    _audit(user, "Diagnosis catalog entry created", diagnosis)
