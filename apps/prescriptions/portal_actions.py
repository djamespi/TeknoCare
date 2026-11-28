"""Portal actions for the prescriptions feature."""
from apps.clinical.models import MedicalRecord
from apps.common.permissions import require_permission
from apps.common.web import validated
from apps.prescriptions.forms import PrescriptionItemForm
from apps.prescriptions.models import Prescription, PrescriptionItem
from apps.prescriptions.services import discard_or_cancel, issue_prescription, prescription_version, remove_item, save_item, start_prescription


def add_prescription_item(actor, data):
    visit = MedicalRecord.objects.get(pk=data["id"])
    require_permission(actor, "prescription.issue", visit)
    if data.get("prescription_id"):
        draft = visit.prescriptions.get(pk=data["prescription_id"])
        version = data["version"]
    else:
        draft = start_prescription(actor=actor, record_id=visit.pk)
        version = prescription_version(draft, [])
    form_values = {**data["item"], "medication": data["item"]["medication_id"], "expected_version": version}
    values = validated(PrescriptionItemForm(form_values))
    medication = values.pop("medication")
    values.pop("expected_version", None)
    save_item(actor=actor, record_id=visit.pk, prescription_id=draft.pk, expected_version=version,
              medication_id=medication.pk, values=values)


def delete_item(actor, data):
    item = PrescriptionItem.objects.select_related("prescription").get(pk=data["id"])
    prescription = item.prescription
    remove_item(actor=actor, record_id=prescription.record_id, prescription_id=prescription.pk,
                expected_version=data["version"], item_id=item.pk)


def prescription_action(actor, data):
    prescription = Prescription.objects.get(pk=data["id"])
    operation = {"issue": issue_prescription, "discard": discard_or_cancel}[data["operation"]]
    operation(actor=actor, record_id=prescription.record_id, prescription_id=prescription.pk, expected_version=data["version"])
