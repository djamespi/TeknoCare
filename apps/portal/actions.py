"""Dispatch portal writes to the feature that owns each operation."""
from apps.appointments import portal_actions as appointments
from apps.billing import portal_actions as billing
from apps.clinical import portal_actions as clinical
from apps.patients import portal_actions as patients
from apps.prescriptions import portal_actions as prescriptions
from apps.profile import portal_actions as profile
from apps.providers import portal_actions as providers
from apps.register import portal_actions as register
from apps.university import portal_actions as university
from apps.user_settings import portal_actions as user_settings


ACTIONS = {
    "add-provider": providers.add_provider,
    "change-charge": billing.change_charge,
    "book": appointments.book,
    "cancel-booking": appointments.cancel,
    "appointment-status": clinical.set_appointment,
    "open-encounter": clinical.open_record,
    "save-notes": clinical.save_notes,
    "change-diagnosis": clinical.change_diagnosis,
    "save-vitals": clinical.save_vitals,
    "finalize": clinical.finalize,
    "add-prescription-item": prescriptions.add_prescription_item,
    "delete-prescription-item": prescriptions.delete_item,
    "prescription-status": prescriptions.prescription_action,
    "referral": clinical.referral,
    "profile": profile.profile,
    "preferences": user_settings.preferences,
    "birth-date": patients.birth_date,
    "contact": patients.update_contact,
    "remove-contact": patients.remove_contact,
    "account-status": register.account_status,
    "add-slots": appointments.add_slots,
    "toggle-slot": appointments.toggle_slot,
    "save-reference": university.save_reference,
}
