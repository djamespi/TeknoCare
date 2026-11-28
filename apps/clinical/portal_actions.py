"""Portal actions for the clinical feature."""
from django.core.exceptions import ValidationError

from apps.appointments.models import Appointment
from apps.clinical.consultation import NOTE_FIELDS, finalize_consultation, record_vitals, save_consultation
from apps.clinical.forms import ReferralForm, VitalSignForm
from apps.clinical.models import MedicalRecord, RecordDiagnosis, Referral
from apps.clinical.reception import change_appointment_status, open_scheduled_encounter
from apps.clinical.referrals import create_referral, update_referral_status
from apps.common.permissions import require_permission
from apps.common.web import validated


def set_appointment(actor, data):
    action = {"checked_in": "check_in", "no_show": "no_show"}[data["status"]]
    return change_appointment_status(actor=actor, appointment_id=data["id"], action=action).pk


def open_record(actor, data):
    appointment = Appointment.objects.select_related("slot", "patient").get(pk=data["id"])
    require_permission(actor, "reception.appointment", appointment)
    existing = MedicalRecord.objects.filter(appointment=appointment).first()
    if existing:
        require_permission(actor, "reception.record", existing)
        return existing.pk
    return open_scheduled_encounter(actor=actor, appointment_id=appointment.pk, provider_id=appointment.slot.provider_id).pk


def save_notes(actor, data):
    visit = MedicalRecord.objects.get(pk=data["id"])
    require_permission(actor, "record.edit", visit)
    links = list(visit.diagnoses.all())
    notes = {field: data["notes"].get(field, getattr(visit, field)) for field in NOTE_FIELDS}
    if any(value is not None and not isinstance(value, str) for value in notes.values()):
        raise ValidationError("Enter plain text in the consultation fields.")
    save_consultation(actor=actor, record_id=visit.pk, expected_version=data["version"], notes=notes,
                      diagnosis_ids=[link.diagnosis_id for link in links],
                      primary_id=next((link.diagnosis_id for link in links if link.is_primary), None))


def change_diagnosis(actor, data):
    action = data["operation"]
    if action == "add":
        visit = MedicalRecord.objects.get(pk=data["id"])
        target_id = data["diagnosis"]
    else:
        link = RecordDiagnosis.objects.select_related("record").get(pk=data["diagnosis"])
        visit, target_id = link.record, link.diagnosis_id
    require_permission(actor, "record.edit", visit)
    links = list(visit.diagnoses.all())
    ids = [link.diagnosis_id for link in links]
    primary = next((link.diagnosis_id for link in links if link.is_primary), None)
    if action == "add" and target_id not in ids:
        ids.append(target_id)
    elif action == "remove":
        ids.remove(target_id)
        if primary == target_id:
            primary = None
    elif action == "primary":
        primary = target_id
    save_consultation(actor=actor, record_id=visit.pk, expected_version=data["version"],
                      notes={field: getattr(visit, field) for field in NOTE_FIELDS}, diagnosis_ids=ids, primary_id=primary)


def save_vitals(actor, data):
    values = validated(VitalSignForm({**data["measurements"], "expected_version": data["version"]}))
    expected_version = values.pop("expected_version")
    record_vitals(actor=actor, record_id=data["id"], expected_version=expected_version, measurements=values)


def finalize(actor, data):
    return finalize_consultation(actor=actor, record_id=data["id"], expected_version=data["version"])


def referral(actor, data):
    if data["operation"] == "add":
        create_referral(actor=actor, record_id=data["id"], **validated(ReferralForm(data)))
    else:
        row = Referral.objects.get(pk=data["id"])
        update_referral_status(actor=actor, record_id=row.record_id, referral_id=row.pk, status=data["status"].title())
