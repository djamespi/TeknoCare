"""Commands behind the Make UI. All clinic mutations go through existing services."""
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.appointments.forms import BookingForm
from apps.appointments.models import Appointment, Slot
from apps.appointments.services import book_appointment, cancel_appointment, save_room, save_slot
from apps.billing.services import save_term, simulate_posting, simulate_void
from apps.clinical.consultation import NOTE_FIELDS, create_diagnosis, finalize_consultation, record_vitals, save_consultation
from apps.clinical.forms import ReferralForm, VitalSignForm
from apps.clinical.models import MedicalRecord, RecordDiagnosis, Referral
from apps.clinical.reception import change_appointment_status, open_scheduled_encounter
from apps.clinical.referrals import create_referral, update_referral_status
from apps.common.permissions import require_permission
from apps.patients.services import remove_emergency_contact, save_emergency_contact, update_birth_date
from apps.prescriptions.forms import PrescriptionItemForm
from apps.prescriptions.models import Prescription, PrescriptionItem
from apps.prescriptions.services import (
    discard_or_cancel, issue_prescription, prescription_version, remove_item, save_item, save_medication,
    start_prescription,
)
from apps.profile.forms import ProfileForm
from apps.profile.models import Profile
from apps.providers.forms import ProviderAccountForm
from apps.register.services import create_provider_account, set_account_status
from apps.university.services import save_department
from apps.user_settings.forms import UserSettingsForm
from apps.user_settings.models import UserSettings


def validated(form):
    if not form.is_valid():
        raise ValidationError([error for errors in form.errors.values() for error in errors])
    return form.cleaned_data


def book(actor, data):
    values = validated(BookingForm({"reason_for_visit": data["reason"], "expected_version": data["version"]}))
    return book_appointment(actor=actor, patient_id=actor.pk, slot_id=data["slot_id"],
                            **values).pk


def cancel(actor, data):
    return cancel_appointment(actor=actor, appointment_id=data["id"]).pk


def add_provider(actor, data):
    require_permission(actor, "accounts.manage")
    form = ProviderAccountForm(data)
    values = validated(form)
    return create_provider_account(
        actor=actor, **form.account_values(), provider_type=values["provider_type"],
        license_number=values["license_number"], specialization=values["specialization"] or None,
    ).pk


def change_charge(actor, data):
    if data.get("confirm") is not True:
        raise ValidationError("Confirm this simulated change first.")
    if data["operation"] == "post":
        return simulate_posting(actor=actor, charge_id=data["id"], confirmed=True).pk
    if data["operation"] == "void":
        return simulate_void(actor=actor, charge_id=data["id"], reason=data["reason"],
                             expected_status=data["status"].title(), confirmed=True).pk
    raise ValidationError("Choose a valid charge action.")


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


def referral(actor, data):
    if data["operation"] == "add":
        create_referral(actor=actor, record_id=data["id"], **validated(ReferralForm(data)))
    else:
        row = Referral.objects.get(pk=data["id"])
        update_referral_status(actor=actor, record_id=row.record_id, referral_id=row.pk, status=data["status"].title())


def update_contact(actor, data):
    if "id" in data:
        contact = actor.patient_profile.emergency_contacts.get(pk=data["id"])
        data = {"full_name": contact.full_name, "relationship": contact.relationship,
                "phone_number": contact.phone_number, "is_primary": True, "contact_id": contact.pk}
    else:
        data = {**{key: data[key] for key in ("full_name", "relationship", "phone_number")},
                "is_primary": bool(data.get("is_primary"))}
        if any(not isinstance(data[field], str) for field in ("full_name", "relationship", "phone_number")):
            raise ValidationError("Enter the contact's name, relationship and phone number.")
    save_emergency_contact(actor=actor, **data)


def profile(actor, data):
    form = ProfileForm(data, instance=Profile.objects.filter(user=actor).first() or Profile(user=actor))
    validated(form)
    form.save()


def preferences(actor, data):
    instance, _ = UserSettings.objects.select_for_update().get_or_create(user=actor)
    form = UserSettingsForm({**{"dark_mode": instance.dark_mode, "email_notifications": instance.email_notifications},
                             **data}, instance=instance)
    validated(form)
    form.save()


def add_slots(actor, data):
    start = timezone.make_aware(datetime.fromisoformat(f'{data["date"]}T{data["from"]}'))
    end = timezone.make_aware(datetime.fromisoformat(f'{data["date"]}T{data["to"]}'))
    minutes = data["minutes"]
    if type(minutes) is not int or not 5 <= minutes <= 180 or start >= end:
        raise ValidationError("Choose a valid time range and slot length.")
    duration = timedelta(minutes=minutes)
    count = 0
    while start + duration <= end:
        save_slot(actor=actor, provider_id=data["provider"], room_id=data["room"],
                  start_time=start, end_time=start + duration, is_active=True)
        start += duration
        count += 1
    if not count:
        raise ValidationError("The time range is shorter than one slot.")
    return count


def toggle_slot(actor, data):
    slot = Slot.objects.get(pk=data["id"])
    return save_slot(actor=actor, provider_id=slot.provider_id, room_id=slot.room_id,
                     start_time=slot.start_time, end_time=slot.end_time, is_active=not slot.is_active,
                     slot_id=slot.pk, expected_version=data["version"]).pk


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


ACTIONS = {
    "add-provider": add_provider,
    "change-charge": change_charge,
    "book": book,
    "cancel-booking": cancel,
    "appointment-status": set_appointment,
    "open-encounter": open_record,
    "save-notes": save_notes,
    "change-diagnosis": change_diagnosis,
    "save-vitals": save_vitals,
    "finalize": lambda actor, data: finalize_consultation(actor=actor, record_id=data["id"], expected_version=data["version"]),
    "add-prescription-item": add_prescription_item,
    "delete-prescription-item": delete_item,
    "prescription-status": prescription_action,
    "referral": referral,
    "profile": profile,
    "preferences": preferences,
    "birth-date": lambda actor, data: update_birth_date(actor=actor, date_of_birth=date.fromisoformat(data["date_of_birth"]) if data.get("date_of_birth") else None),
    "contact": update_contact,
    "remove-contact": lambda actor, data: remove_emergency_contact(actor=actor, contact_id=data["id"]),
    "account-status": lambda actor, data: set_account_status(actor=actor, user_id=data["id"], status=data["status"].title()),
    "add-slots": add_slots,
    "toggle-slot": toggle_slot,
    "save-reference": save_reference,
}
