"""Role-scoped read models consumed by the Make frontend."""
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.appointments.booking_views import _bookable_slots
from apps.appointments.models import Appointment, ClinicRoom, Slot
from apps.audit.models import AuditLog
from apps.billing.models import AcademicTerm, StudentCharge
from apps.clinical.consultation import consultation_version
from apps.clinical.models import Diagnosis, MedicalRecord, RecordDiagnosis, Referral, VitalSign
from apps.clinical.reception_views import _visible_appointments
from apps.common.permissions import allowed, clinical_provider
from apps.patients.models import EmergencyContact, Patient, PatientAllergy
from apps.prescriptions.models import Medication, Prescription, PrescriptionItem
from apps.prescriptions.services import prescription_version
from apps.profile.models import Profile
from apps.providers.eligibility import eligible_providers
from apps.providers.models import Provider
from apps.register.models import User
from apps.university.models import Department
from apps.user_settings.models import UserSettings


def rows(query, fields, *, lower=()):
    result = list(query.values(*fields.split()))
    for row in result:
        for field in lower:
            if row[field]:
                row[field] = row[field].lower()
    return result


def user_rows(query):
    return rows(query, "user_id school_id fname lname email user_type account_status created_at",
                lower=("user_type", "account_status"))


def record_rows(actor, query):
    records, full, vitals = [], [], []
    fields = ("record_id appointment_id patient_id provider_id chief_complaint affiliation_at_visit "
              "symptoms examination_notes treatment_plan status visited_at finalized_at")
    for visit in query.select_related("patient__patient", "provider__provider", "appointment").iterator():
        own = visit.patient_id == actor.pk
        chart = not own and allowed(actor, "record.view", visit)
        triage = allowed(actor, "vitals.record", visit)
        if not (chart or triage or (own and visit.status == MedicalRecord.Status.FINALIZED)):
            continue
        record = {field: getattr(visit, field) for field in fields.split()}
        record["status"] = visit.status.lower()
        record["affiliation_at_visit"] = (visit.affiliation_at_visit or "").lower() or None
        if not chart:
            for field in ("symptoms", "examination_notes", "treatment_plan"):
                record[field] = None
        if not (chart or own):
            record["chief_complaint"] = ""
        record.update(can_edit=allowed(actor, "record.edit", visit), can_record_vitals=triage,
                      can_finalize=allowed(actor, "record.finalize", visit),
                      can_prescribe=allowed(actor, "prescription.issue", visit),
                      can_refer=allowed(actor, "referral.create", visit))
        if record["can_edit"] or triage:
            record["version"] = consultation_version(
                visit, visit.diagnoses.all(), visit.vital_signs.order_by("-pk").values_list("pk", flat=True).first(),
            )
        if chart:
            full.append(visit.pk)
        if chart or triage or (own and getattr(settings, "TEKNOCARE_MAKE_DEMO", False)):
            vitals.append(visit.pk)
        records.append(record)
    return records, full, vitals


def portal_data(actor):
    provider = clinical_provider(actor)
    role = actor.user_type
    accounts = User.objects.filter(pk=actor.pk)
    own = Patient.objects.filter(pk=actor.pk)
    patient_rows = own
    allergies = PatientAllergy.objects.filter(patient__in=own)
    appointments = Appointment.objects.filter(patient__in=own)
    bookable = _bookable_slots() if own.exists() else Slot.objects.none()
    slots = Slot.objects.none()
    providers = eligible_providers()
    records, full, vitals = [], [], []
    document_records = MedicalRecord.objects.filter(patient__in=own, status="Finalized")
    charges = StudentCharge.objects.filter(record__patient__in=own)
    audit = AuditLog.objects.none()
    terms = AcademicTerm.objects.filter(pk__in=charges.values("term_id"))
    diagnoses = Diagnosis.objects.none()
    medications = Medication.objects.none()
    rooms = ClinicRoom.objects.none()
    if actor.is_staff:
        accounts = User.objects.all()
        patient_rows = Patient.objects.all()
        providers = Provider.objects.all()
        appointments = Appointment.objects.all()
        slots = Slot.objects.all()
        charges = StudentCharge.objects.all()
        audit = AuditLog.objects.order_by("-logged_at", "-pk")[:300]
        terms, diagnoses, medications, rooms = (
            AcademicTerm.objects.all(), Diagnosis.objects.all(), Medication.objects.all(), ClinicRoom.objects.all(),
        )
    elif provider:
        appointments = appointments | _visible_appointments(actor)
        scope = Q(provider=provider) | Q(patient__in=own, status="Finalized")
        if provider.provider_type == Provider.Type.NURSE:
            scope |= Q(visited_at__date=timezone.localdate(), status="Draft")
        candidate = MedicalRecord.objects.filter(scope)
        possible_patients = Patient.objects.filter(
            Q(pk__in=candidate.values("patient_id")) | Q(pk__in=appointments.values("patient_id")),
        )
        care_ids = [p.pk for p in possible_patients if allowed(actor, "patient.view", p)]
        candidate = candidate | MedicalRecord.objects.filter(patient_id__in=care_ids, status="Finalized")
        records, full, vitals = record_rows(actor, candidate)
        visible_ids = {r["patient_id"] for r in records}
        patient_rows = Patient.objects.filter(Q(pk__in=visible_ids) | Q(pk__in=care_ids) | Q(pk__in=own))
        allergies = PatientAllergy.objects.filter(patient_id__in=care_ids)
        providers = providers | Provider.objects.filter(pk=actor.pk)
        slots = Slot.objects.filter(provider=provider)
        diagnoses, medications, rooms = Diagnosis.objects.all(), Medication.objects.all(), ClinicRoom.objects.filter(is_active=True)
    if not provider or actor.is_staff:
        records, full, vitals = record_rows(actor, document_records)

    own_finalized_ids = [r["record_id"] for r in records if r["patient_id"] == actor.pk and r["status"] == "finalized"]
    document_ids = full + own_finalized_ids
    linked_diagnoses = RecordDiagnosis.objects.filter(record_id__in=document_ids)
    prescriptions = Prescription.objects.filter(
        Q(record_id__in=full, status="Issued") | Q(record_id__in=own_finalized_ids, status="Issued")
        | Q(record__provider_id=actor.pk, record_id__in=full),
    )
    items = PrescriptionItem.objects.filter(prescription__in=prescriptions)
    diagnoses = diagnoses | Diagnosis.objects.filter(pk__in=linked_diagnoses.values("diagnosis_id"))
    medications = medications | Medication.objects.filter(pk__in=items.values("medication_id"))
    slots = slots | bookable | Slot.objects.filter(pk__in=appointments.values("slot_id"))
    providers = providers | Provider.objects.filter(
        Q(pk__in=slots.values("provider_id")) | Q(pk__in=[r["provider_id"] for r in records])
        | Q(pk__in=prescriptions.values("prescriber_id")),
    )
    rooms = rooms | ClinicRoom.objects.filter(pk__in=slots.values("room_id"))
    accounts = accounts | User.objects.filter(
        Q(pk__in=providers.values("pk")) | Q(pk__in=patient_rows.values("pk")) | Q(pk__in=appointments.values("patient_id")),
    )

    users = user_rows(accounts)
    if not actor.is_staff:
        for user in users:
            if user["user_id"] != actor.pk:
                user["email"] = ""
                if user["user_type"] != "patient" or role != "Provider":
                    user["school_id"] = ""
    cancellable = {row.pk for row in appointments.filter(patient__in=own, status="Scheduled", slot__start_time__gt=timezone.now(),
                                                        medical_record__isnull=True)}
    visits = rows(appointments, "appointment_id patient_id slot_id reason_for_visit status created_at canceled_at")
    statuses = {"Scheduled": "booked", "Checked-In": "checked_in", "Completed": "completed",
                "Canceled": "canceled", "No Show": "no_show"}
    for visit in visits:
        visit["status"] = statuses[visit["status"]]
        visit["can_cancel"] = visit["appointment_id"] in cancellable
        if visit["patient_id"] != actor.pk:
            visit["reason_for_visit"] = ""

    profiles = rows(Profile.objects.filter(user=actor), "user_id phone_number home_address bio")
    settings = rows(UserSettings.objects.filter(user=actor), "user_id dark_mode email_notifications")
    if not settings:
        settings = [{"user_id": actor.pk, "dark_mode": False, "email_notifications": False}]
    patient_data = rows(patient_rows, "patient_id department_id affiliation date_of_birth medical_history_summary created_at",
                        lower=("affiliation",))
    for patient in patient_data:
        if patient["patient_id"] != actor.pk:
            patient["medical_history_summary"] = None
    slot_data = rows(slots, "slot_id provider_id room_id start_time end_time is_active")
    open_versions = {slot.pk: slot.version for slot in bookable}
    slot_versions = {slot.pk: slot.version for slot in slots if actor.is_staff or (provider and slot.provider_id == actor.pk)}
    for slot in slot_data:
        slot_id = slot["slot_id"]
        slot["bookable"] = slot_id in open_versions
        if slot_id in open_versions or slot_id in slot_versions:
            slot["version"] = slot_versions.get(slot_id, open_versions.get(slot_id))
    eligible_ids = set(eligible_providers().values_list("pk", flat=True))
    provider_data = rows(providers, "provider_id provider_type specialization license_number is_active", lower=("provider_type",))
    for entry in provider_data:
        entry["eligible"] = entry["provider_id"] in eligible_ids
        if not actor.is_staff and entry["provider_id"] != actor.pk:
            entry["license_number"] = None
    prescription_data = rows(prescriptions, "prescription_id record_id prescriber_id issued_at status", lower=("status",))
    editable = prescriptions.filter(status="Draft", prescriber_id=actor.pk).prefetch_related("items")
    prescription_versions = {row.pk: prescription_version(row, row.items.all()) for row in editable}
    for entry in prescription_data:
        if entry["prescription_id"] in prescription_versions:
            entry["version"] = prescription_versions[entry["prescription_id"]]
    diagnosis_data = rows(linked_diagnoses, "record_diagnosis_id record_id diagnosis_id is_primary notes")
    for entry in diagnosis_data:
        if entry["record_id"] not in full:
            entry["notes"] = None

    charge_data = rows(charges, "charge_id charge_code record_id record__patient_id term_id created_by_user_id description amount currency_code "
                                "status billing_reference reversal_reference created_at posted_at voided_at void_reason",
                       lower=("status",))
    for charge in charge_data:
        charge["patient_id"] = charge.pop("record__patient_id")
        charge["amount"] = float(charge["amount"])
    vital_data = rows(VitalSign.objects.filter(record_id__in=vitals),
                      "vital_id record_id recorded_by_user_id recorded_at temperature_c systolic_mmhg diastolic_mmhg "
                      "pulse_bpm respiratory_rate oxygen_saturation_pct height_cm weight_kg")
    return {
        "department": rows(Department.objects.all(), "department_id code name is_active"),
        "user": users, "patient": patient_data,
        "provider": provider_data,
        "user_profile": profiles, "user_settings": settings,
        "emergency_contact": rows(EmergencyContact.objects.filter(patient__in=own),
                                  "contact_id patient_id full_name relationship phone_number is_primary"),
        "patient_allergy": rows(allergies, "allergy_id patient_id allergen reaction severity recorded_at", lower=("severity",)),
        "clinic_room": rows(rooms, "room_id campus building room_number is_active"),
        "slot": slot_data, "appointment": visits, "medical_record": records, "vital_sign": vital_data,
        "diagnosis": rows(diagnoses, "diagnosis_id code description coding_system"),
        "record_diagnosis": diagnosis_data,
        "medication": rows(medications, "medication_id medication_code generic_name strength dosage_form is_active"),
        "prescription": prescription_data,
        "prescription_item": rows(items, "item_id prescription_id medication_id dose route frequency duration_days quantity quantity_unit instructions"),
        "referral": rows(Referral.objects.filter(record_id__in=document_ids),
                         "referral_id record_id referred_by_provider_id destination reason status referred_at", lower=("status",)),
        "academic_term": rows(terms, "term_id academic_year semester start_date end_date is_open_for_charges"),
        "student_charge": charge_data,
        "audit_log": rows(audit, "log_id actor_user_id action_performed target_table target_record_id logged_at"),
    }
