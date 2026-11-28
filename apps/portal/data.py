"""Role-scoped read models consumed by the Make frontend."""
from functools import partial

from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from apps.appointments.booking_views import _bookable_slots
from apps.appointments.models import Appointment, ClinicRoom, Slot
from apps.audit.models import AuditLog
from apps.billing.models import AcademicTerm, StudentCharge
from apps.clinical.consultation import consultation_version
from apps.clinical.models import Diagnosis, MedicalRecord, RecordDiagnosis, Referral, VitalSign
from apps.clinical.reception_views import _visible_appointments
from apps.common.permissions import allowed, clinical_provider, required_profile_exists
from apps.patients.models import EmergencyContact, Patient, PatientAllergy
from apps.prescriptions.models import Medication, Prescription, PrescriptionItem
from apps.prescriptions.services import prescription_version
from apps.profile.models import Profile
from apps.providers.eligibility import eligible_providers
from apps.providers.models import Provider
from apps.register.models import User
from apps.university.models import Department
from apps.user_settings.models import UserSettings


SAMPLE_PROVIDER_PHOTOS = {"MD-1048": "mara-villareal", "RN-2073": "joel-macaraeg"}


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


def record_rows(actor, query, permits, *, include_versions):
    records, full, vitals = [], [], []
    fields = ("record_id appointment_id patient_id provider_id chief_complaint affiliation_at_visit "
              "symptoms examination_notes treatment_plan status visited_at finalized_at")
    for visit in query.select_related("patient__patient", "provider__provider", "appointment").iterator():
        own = visit.patient_id == actor.pk
        chart = not own and permits("record.view", visit)
        triage = permits("vitals.record", visit)
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
        record.update(can_edit=permits("record.edit", visit), can_record_vitals=triage,
                      can_finalize=permits("record.finalize", visit),
                      can_prescribe=permits("prescription.issue", visit),
                      can_refer=permits("referral.create", visit))
        if include_versions and (record["can_edit"] or triage):
            record["version"] = consultation_version(
                visit, visit.diagnoses.all(), visit.vital_signs.order_by("-pk").values_list("pk", flat=True).first(),
            )
        if chart:
            full.append(visit.pk)
        if chart or triage or (own and getattr(settings, "TEKNOCARE_MAKE_DEMO", False)):
            vitals.append(visit.pk)
        records.append(record)
    return records, full, vitals


def preference_rows(actor):
    return rows(UserSettings.objects.filter(user=actor), "user_id dark_mode email_notifications") or [
        {"user_id": actor.pk, "dark_mode": False, "email_notifications": False},
    ]


def charge_rows(charges):
    result = rows(charges, "charge_id charge_code record_id record__patient_id term_id created_by_user_id description amount currency_code "
                           "status billing_reference reversal_reference created_at posted_at voided_at void_reason", lower=("status",))
    for charge in result:
        charge["patient_id"] = charge.pop("record__patient_id")
        charge["amount"] = float(charge["amount"])
    return result


def portal_data(actor, tables=None):
    own = Patient.objects.filter(pk=actor.pk)
    result = {}

    def needs(*names):
        return any(name not in result and (tables is None or name in tables) for name in names)

    def read(name, query, fields, *, lower=()):
        if needs(name):
            result[name] = rows(query, fields, lower=lower)

    read("department", Department.objects.all(), "department_id code name is_active")
    read("user_profile", Profile.objects.filter(user=actor), "user_id phone_number home_address bio")
    read("emergency_contact", EmergencyContact.objects.filter(patient__in=own),
         "contact_id patient_id full_name relationship phone_number is_primary")
    if needs("user_settings"):
        result["user_settings"] = preference_rows(actor)
    audit = AuditLog.objects.order_by("-logged_at", "-pk")[:300] if actor.is_staff else AuditLog.objects.none()
    read("audit_log", audit, "log_id actor_user_id action_performed target_table target_record_id logged_at")
    charges = StudentCharge.objects.all() if actor.is_staff else StudentCharge.objects.filter(record__patient__in=own)
    if needs("student_charge"):
        result["student_charge"] = charge_rows(charges)
    terms = AcademicTerm.objects.all() if actor.is_staff else AcademicTerm.objects.filter(pk__in=charges.values("term_id"))
    read("academic_term", terms, "term_id academic_year semester start_date end_date is_open_for_charges")
    if actor.is_staff:
        read("clinic_room", ClinicRoom.objects.all(), "room_id campus building room_number is_active")
        read("diagnosis", Diagnosis.objects.all(), "diagnosis_id code description coding_system")
        read("medication", Medication.objects.all(), "medication_id medication_code generic_name strength dosage_form is_active")
        if needs("user"):
            result["user"] = user_rows(User.objects.all())
    if tables is not None and tables <= result.keys():
        return result

    provider = clinical_provider(actor)
    role = actor.user_type
    accounts = User.objects.filter(pk=actor.pk)
    has_patient = own.exists() if role == "Patient" or needs("slot", "user", "provider", "clinic_room") else False
    has_profile = has_patient if role == "Patient" else bool(provider) or required_profile_exists(actor)
    # These checks share account and provider facts only within this snapshot.
    permits = partial(allowed, actor, has_profile=has_profile, provider=provider)
    patient_rows = own
    allergies = PatientAllergy.objects.filter(patient__in=own)
    appointments = Appointment.objects.filter(patient__in=own)
    bookable = _bookable_slots() if has_patient else Slot.objects.none()
    slots = Slot.objects.none()
    providers = eligible_providers()
    records, full, vitals = [], [], []
    document_records = MedicalRecord.objects.filter(patient__in=own, status="Finalized")
    diagnoses = Diagnosis.objects.none()
    medications = Medication.objects.none()
    rooms = ClinicRoom.objects.none()
    need_records = (
        needs("medical_record", "record_diagnosis", "vital_sign", "prescription", "prescription_item", "referral")
        or (not actor.is_staff and needs("diagnosis", "medication", "provider", "user"))
        or (not actor.is_staff and provider and needs("patient", "patient_allergy"))
    )
    if actor.is_staff:
        patient_rows = Patient.objects.all()
        providers = Provider.objects.all()
        appointments = Appointment.objects.all()
        slots = Slot.objects.all()
    elif provider:
        appointments = appointments | _visible_appointments(actor)
        if need_records:
            scope = Q(provider=provider) | Q(patient__in=own, status="Finalized")
            if provider.provider_type == Provider.Type.NURSE:
                scope |= Q(visited_at__date=timezone.localdate(), status="Draft")
            candidate = MedicalRecord.objects.filter(scope)
            possible_patients = Patient.objects.filter(
                Q(pk__in=candidate.values("patient_id")) | Q(pk__in=appointments.values("patient_id")),
            )
            care_ids = [p.pk for p in possible_patients if permits("patient.view", p)]
            candidate = candidate | MedicalRecord.objects.filter(patient_id__in=care_ids, status="Finalized")
            records, full, vitals = record_rows(actor, candidate, permits, include_versions=needs("medical_record"))
            visible_ids = {r["patient_id"] for r in records}
            patient_rows = Patient.objects.filter(Q(pk__in=visible_ids) | Q(pk__in=care_ids) | Q(pk__in=own))
            allergies = PatientAllergy.objects.filter(patient_id__in=care_ids)
        providers = providers | Provider.objects.filter(pk=actor.pk)
        slots = Slot.objects.filter(provider=provider)
        diagnoses, medications, rooms = Diagnosis.objects.all(), Medication.objects.all(), ClinicRoom.objects.filter(is_active=True)
    if need_records and (not provider or actor.is_staff):
        records, full, vitals = record_rows(actor, document_records, permits, include_versions=needs("medical_record"))

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

    if needs("user"):
        users = user_rows(accounts)
        for user in users:
            if user["user_id"] != actor.pk:
                user["email"] = ""
                if user["user_type"] != "patient" or role != "Provider":
                    user["school_id"] = ""
        result["user"] = users
    if needs("appointment"):
        cancellable = Appointment.objects.filter(pk=OuterRef("pk"), patient__in=own, status="Scheduled",
                                                 slot__start_time__gt=timezone.now(), medical_record__isnull=True)
        read("appointment", appointments.annotate(can_cancel=Exists(cancellable)),
             "appointment_id patient_id slot_id reason_for_visit status created_at canceled_at can_cancel")
        statuses = {"Scheduled": "booked", "Checked-In": "checked_in", "Completed": "completed",
                    "Canceled": "canceled", "No Show": "no_show"}
        for visit in result["appointment"]:
            visit["status"] = statuses[visit["status"]]
            if visit["patient_id"] != actor.pk:
                visit["reason_for_visit"] = ""

    if needs("patient"):
        read("patient", patient_rows, "patient_id department_id affiliation date_of_birth medical_history_summary created_at",
             lower=("affiliation",))
        for patient in result["patient"]:
            if patient["patient_id"] != actor.pk:
                patient["medical_history_summary"] = None
    if needs("slot"):
        slot_data = []
        slot_fields = ("slot_id", "provider_id", "room_id", "start_time", "end_time", "is_active", "bookable")
        for slot in slots.select_related(None).annotate(bookable=Exists(bookable.filter(pk=OuterRef("pk")))):
            entry = {field: getattr(slot, field) for field in slot_fields}
            if slot.bookable or actor.is_staff or (provider and slot.provider_id == actor.pk):
                entry["version"] = slot.version
            slot_data.append(entry)
        result["slot"] = slot_data
    if needs("provider"):
        eligible_ids = set(eligible_providers().values_list("pk", flat=True))
        provider_fields = "provider_id provider_type specialization license_number is_active"
        use_sample_photos = getattr(settings, "TEKNOCARE_MAKE_DEMO", False)
        if use_sample_photos:
            provider_fields += " provider__school_id"
        read("provider", providers, provider_fields, lower=("provider_type",))
        for entry in result["provider"]:
            if use_sample_photos:
                photo = SAMPLE_PROVIDER_PHOTOS.get(entry.pop("provider__school_id"))
                if photo:
                    entry["booking_photo"] = photo
            entry["eligible"] = entry["provider_id"] in eligible_ids
            if not actor.is_staff and entry["provider_id"] != actor.pk:
                entry["license_number"] = None
    if needs("prescription"):
        read("prescription", prescriptions, "prescription_id record_id prescriber_id issued_at status", lower=("status",))
        editable = prescriptions.filter(status="Draft", prescriber_id=actor.pk).prefetch_related("items")
        versions = {row.pk: prescription_version(row, row.items.all()) for row in editable}
        for entry in result["prescription"]:
            if entry["prescription_id"] in versions:
                entry["version"] = versions[entry["prescription_id"]]
    if needs("record_diagnosis"):
        read("record_diagnosis", linked_diagnoses, "record_diagnosis_id record_id diagnosis_id is_primary notes")
        for entry in result["record_diagnosis"]:
            if entry["record_id"] not in full:
                entry["notes"] = None
    if needs("medical_record"):
        result["medical_record"] = records
    read("patient_allergy", allergies, "allergy_id patient_id allergen reaction severity recorded_at", lower=("severity",))
    read("clinic_room", rooms, "room_id campus building room_number is_active")
    read("vital_sign", VitalSign.objects.filter(record_id__in=vitals),
         "vital_id record_id recorded_by_user_id recorded_at temperature_c systolic_mmhg diastolic_mmhg "
         "pulse_bpm respiratory_rate oxygen_saturation_pct height_cm weight_kg")
    read("diagnosis", diagnoses, "diagnosis_id code description coding_system")
    read("medication", medications, "medication_id medication_code generic_name strength dosage_form is_active")
    read("prescription_item", items, "item_id prescription_id medication_id dose route frequency duration_days quantity quantity_unit instructions")
    read("referral", Referral.objects.filter(record_id__in=document_ids),
         "referral_id record_id referred_by_provider_id destination reason status referred_at", lower=("status",))
    return result
