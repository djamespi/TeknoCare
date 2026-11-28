"""Portal actions for the patients feature."""
from datetime import date

from django.core.exceptions import ValidationError

from apps.patients.services import remove_emergency_contact, save_emergency_contact, update_birth_date


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


def birth_date(actor, data):
    birthday = date.fromisoformat(data["date_of_birth"]) if data.get("date_of_birth") else None
    return update_birth_date(actor=actor, date_of_birth=birthday)


def remove_contact(actor, data):
    return remove_emergency_contact(actor=actor, contact_id=data["id"])
