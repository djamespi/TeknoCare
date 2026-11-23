"""Scoped writes for patient details, emergency contacts and allergies."""
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditLog
from apps.common.permissions import require_permission
from apps.university.models import Department

from .models import EmergencyContact, Patient, PatientAllergy


def _audit(actor, action, target):
    AuditLog.objects.create(
        actor_user=actor, action_performed=action, target_table=target._meta.db_table, target_record_id=target.pk
    )


@transaction.atomic
def update_birth_date(*, actor, date_of_birth):
    user = require_permission(actor, "account.use")
    patient = Patient.objects.select_for_update().get(pk=user.pk)
    patient.date_of_birth = date_of_birth
    patient.save(update_fields=["date_of_birth"])
    _audit(user, "Patient birth date updated", patient)


@transaction.atomic
def save_emergency_contact(*, actor, full_name, relationship, phone_number, is_primary, contact_id=None):
    user = require_permission(actor, "account.use")
    patient = Patient.objects.select_for_update().get(pk=user.pk)
    contacts = patient.emergency_contacts
    contact = contacts.get(pk=contact_id) if contact_id is not None else EmergencyContact(patient=patient)
    contact.full_name = full_name.strip()
    contact.relationship = relationship.strip()
    contact.phone_number = phone_number.strip()
    contact.is_primary = is_primary
    if contact.is_primary:
        contacts.filter(is_primary=True).exclude(pk=contact.pk).update(is_primary=False)
    contact.save()
    _audit(user, "Emergency contact added" if contact_id is None else "Emergency contact updated", contact)


@transaction.atomic
def remove_emergency_contact(*, actor, contact_id):
    user = require_permission(actor, "account.use")
    patient = Patient.objects.select_for_update().get(pk=user.pk)
    contact = patient.emergency_contacts.get(pk=contact_id)
    _audit(user, "Emergency contact removed", contact)
    contact.delete()


@transaction.atomic
def update_affiliation(*, actor, patient_id, affiliation, department):
    user = require_permission(actor, "accounts.manage")
    patient = Patient.objects.select_for_update().get(pk=patient_id)
    if not affiliation and patient.affiliation is not None:
        raise ValidationError({"affiliation": "Choose a known affiliation."})
    department_id = department.pk if department else None
    if department_id is not None and department_id != patient.department_id:
        if not Department.objects.select_for_update().filter(pk=department_id, is_active=True).exists():
            raise ValidationError({"department": "Choose an active department or leave it unspecified."})
    patient.affiliation = affiliation or None
    patient.department_id = department_id
    patient.save(update_fields=["affiliation", "department"])
    _audit(user, "Patient affiliation details updated", patient)


@transaction.atomic
def save_allergy(*, actor, patient_id, allergen, reaction, severity, allergy_id=None):
    patient = Patient.objects.select_for_update().get(pk=patient_id)
    user = require_permission(actor, "patient.allergy_edit", patient)
    allergy = patient.allergies.get(pk=allergy_id) if allergy_id is not None else PatientAllergy(patient=patient)
    allergy.allergen = allergen.strip()
    allergy.reaction = (reaction or "").strip()
    allergy.severity = severity
    allergy.save()
    _audit(user, "Patient allergy recorded" if allergy_id is None else "Patient allergy updated", allergy)
