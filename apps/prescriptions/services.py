"""Clinical and catalog writes for the prototype prescription workflow."""
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.clinical.models import MedicalRecord
from apps.clinical.reception import lock_encounter_for_update
from apps.common.permissions import require_permission

from .models import Medication, Prescription, PrescriptionItem


ITEM_FIELDS = ("dose", "route", "frequency", "duration_days", "quantity", "quantity_unit", "instructions")


def _audit(actor, action, target):
    AuditLog.objects.create(actor_user=actor, action_performed=action,
        target_table=target._meta.db_table, target_record_id=target.pk)


def prescription_version(prescription, items):
    values = [prescription.pk, prescription.status, prescription.record_id, prescription.prescriber_id,
        [[item.pk, item.medication_id, *(getattr(item, field) for field in ITEM_FIELDS)]
            for item in sorted(items, key=lambda line: line.pk)]]
    return salted_hmac("prescriptions.version", json.dumps(values, default=str), algorithm="sha256").hexdigest()


def _lock_visit(actor, record_id, action, require_draft=False):
    actor = require_permission(actor, "consultation.access")
    snapshot = MedicalRecord.objects.get(pk=record_id)
    require_permission(actor, action, snapshot)
    visit = lock_encounter_for_update(snapshot, actor_id=actor.pk)
    actor = require_permission(actor, action, visit)
    if require_draft and visit.appointment_id and visit.appointment.status != Appointment.Status.CHECKED_IN:
        raise ValidationError("The appointment must be Checked in before prescribing.")
    return actor, visit


def _start_draft(actor, visit):
    if visit.prescriptions.filter(status=Prescription.Status.DRAFT).exists():
        raise ValidationError("Resolve the existing prescription draft before starting another.")
    draft = Prescription.objects.create(record=visit, prescriber_id=actor.pk)
    _audit(actor, "Prescription draft opened", draft)
    return draft


def _lock_prescription(actor, record_id, prescription_id, action, expected_version):
    actor, visit = _lock_visit(actor, record_id, action, require_draft=action == "prescription.issue")
    prescription = visit.prescriptions.select_for_update().get(pk=prescription_id)
    items = list(prescription.items.select_for_update().order_by("pk"))
    if not constant_time_compare(prescription_version(prescription, items), expected_version or ""):
        raise ValidationError("This prescription changed. Reload and review it before saving.")
    return actor, prescription, items


def _require_owned_draft(actor, prescription):
    if prescription.status != Prescription.Status.DRAFT or prescription.prescriber_id != actor.pk:
        raise ValidationError("Only your own prescription draft is editable.")


@transaction.atomic
def start_prescription(*, actor, record_id):
    actor, visit = _lock_visit(actor, record_id, "prescription.issue", require_draft=True)
    return _start_draft(actor, visit)


@transaction.atomic
def save_item(*, actor, record_id, prescription_id, expected_version, medication_id, values, item_id=None):
    actor, prescription, items = _lock_prescription(actor, record_id, prescription_id, "prescription.issue", expected_version)
    _require_owned_draft(actor, prescription)
    medication = Medication.objects.select_for_update().filter(pk=medication_id, is_active=True).first()
    if medication is None:
        raise ValidationError({"medication": "Choose an active medication catalog entry."})
    item = PrescriptionItem(prescription=prescription) if item_id is None else next(
        (line for line in items if line.pk == item_id), None,
    )
    if item is None:
        raise ValidationError("This item no longer belongs to the prescription.")
    item.medication = medication
    for field in ITEM_FIELDS:
        value = values.get(field)
        setattr(item, field, value.strip() if isinstance(value, str) else value)
    item.save()
    _audit(actor, "Prescription item added" if item_id is None else "Prescription item updated", item)


@transaction.atomic
def remove_item(*, actor, record_id, prescription_id, expected_version, item_id):
    actor, prescription, items = _lock_prescription(actor, record_id, prescription_id, "prescription.issue", expected_version)
    _require_owned_draft(actor, prescription)
    item = next((line for line in items if line.pk == item_id), None)
    if item is None:
        raise ValidationError("This item no longer belongs to the prescription.")
    _audit(actor, "Prescription item removed", item)
    item.delete()


@transaction.atomic
def issue_prescription(*, actor, record_id, prescription_id, expected_version):
    actor, prescription, items = _lock_prescription(actor, record_id, prescription_id, "prescription.issue", expected_version)
    _require_owned_draft(actor, prescription)
    if not items:
        raise ValidationError("Add at least one medicine before issuing the prescription.")
    medications = Medication.objects.select_for_update().filter(pk__in={item.medication_id for item in items}).order_by("pk")
    if any(not medication.is_active for medication in medications):
        raise ValidationError("Replace or remove inactive medications before issuing.")
    for item in items:
        item.prescription = prescription
        item.full_clean()
    prescription.status = Prescription.Status.ISSUED
    prescription.issued_at = timezone.now()
    prescription.save(update_fields=["status", "issued_at"])
    _audit(actor, "Prescription issued", prescription)


@transaction.atomic
def discard_or_cancel(*, actor, record_id, prescription_id, expected_version):
    actor, prescription, _ = _lock_prescription(actor, record_id, prescription_id, "prescription.correct", expected_version)
    if prescription.status == Prescription.Status.CANCELED:
        raise ValidationError("This prescription is already canceled.")
    was_issued = prescription.status == Prescription.Status.ISSUED
    prescription.status = Prescription.Status.CANCELED
    prescription.save(update_fields=["status"])
    _audit(actor, "Issued prescription canceled" if was_issued else "Prescription draft discarded", prescription)


@transaction.atomic
def start_replacement(*, actor, old_prescription_id, record_id):
    actor, visit = _lock_visit(actor, record_id, "prescription.issue", require_draft=True)
    old = Prescription.objects.select_for_update(of=("self",)).filter(
        pk=old_prescription_id, status=Prescription.Status.CANCELED, issued_at__isnull=False, record__patient_id=visit.patient_id,
    ).first()
    if old is None:
        raise ValidationError("Choose a canceled issued prescription for this patient.")
    require_permission(actor, "prescription.correct", old.record)
    action = f"Replacement draft for prescription #{old.pk}"
    replacements = Prescription.objects.exclude(status=Prescription.Status.CANCELED, issued_at__isnull=True)
    if AuditLog.objects.filter(action_performed=action, target_table="prescription",
        target_record_id__in=replacements.values("pk")).exists():
        raise ValidationError("A replacement has already been started for this prescription.")
    draft = _start_draft(actor, visit)
    _audit(actor, action, draft)
    return draft


@transaction.atomic
def save_medication(*, actor, values, medication_id=None):
    actor = require_permission(actor, "reference.manage")
    medication = Medication.objects.select_for_update().get(pk=medication_id) if medication_id else Medication()
    for field in ("medication_code", "generic_name", "strength", "dosage_form", "is_active"):
        value = values[field]
        setattr(medication, field, value.strip() if isinstance(value, str) else value)
    medication.save()
    _audit(actor, "Medication catalog entry updated" if medication_id else "Medication catalog entry created", medication)
