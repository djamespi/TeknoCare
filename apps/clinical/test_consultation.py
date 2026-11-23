from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.common.test_data import clinic_data
from apps.patients.models import Patient, PatientAllergy

from .consultation import consultation_version, finalize_consultation, record_vitals, save_consultation
from .models import Diagnosis, MedicalRecord, RecordDiagnosis, Referral, VitalSign
from .reception import assign_encounter, open_scheduled_encounter, open_walkin_encounter
from .test_reception import attending


class ConsultationWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.physician, cls.slot, cls.previous = clinic_data()
        cls.nurse = attending("Nurse")
        cls.dentist = attending("Dentist")
        cls.visit = open_walkin_encounter(actor=cls.admin, patient_id=cls.patient.pk, provider_id=cls.physician.pk)
        cls.first = Diagnosis.objects.create(coding_system="Prototype", code="DEMO-A", description="Fictional finding A")
        cls.second = Diagnosis.objects.create(coding_system="Prototype", code="DEMO-B", description="Fictional finding B")
        cls.notes = {"chief_complaint": "Fictional chief complaint", "examination_notes": "Fictional examination",
            "treatment_plan": "Fictional follow-up plan"}

    def workspace(self, visit=None):
        return reverse("consultation:workspace", args=[(visit or self.visit).pk])

    def revision(self, visit=None):
        visit = MedicalRecord.objects.get(pk=(visit or self.visit).pk)
        return consultation_version(visit, visit.diagnoses.all(), visit.vital_signs.order_by("-pk").values_list("pk", flat=True).first())

    def save_notes(self, visit=None, diagnoses=(), primary=None):
        visit = visit or self.visit
        return save_consultation(actor=self.physician.provider, record_id=visit.pk, expected_version=self.revision(visit),
            notes=self.notes, diagnosis_ids=diagnoses, primary_id=primary)

    def test_nurse_has_vitals_and_allergies_without_notes_history_or_finalize(self):
        self.save_notes(diagnoses=(self.first.pk,))
        PatientAllergy.objects.create(patient=self.patient, allergen="Fictional allergen")
        self.client.force_login(self.nurse.provider)
        result = self.client.get(self.workspace())
        self.assertContains(result, "Fictional allergen")
        self.assertContains(result, "Save vital signs")
        for private in ("Fictional chief complaint", "Fictional finding A", "Recent finalized visits", "Finalize encounter"):
            self.assertNotContains(result, private)
        url = self.workspace()
        for action in ("notes", "finalize"):
            self.assertEqual(self.client.post(url, {"action": action}).status_code, 403)
        self.assertRedirects(self.client.post(url, {"action": "vitals", "vitals-expected_version": self.revision(),
            "vitals-pulse_bpm": "75", "vitals-recorded_by_user": self.admin.pk}), url)
        reading = self.visit.vital_signs.get()
        self.assertEqual((reading.recorded_by_user_id, reading.pulse_bpm), (self.nurse.pk, 75))
        self.assertTrue(AuditLog.objects.filter(actor_user_id=self.nurse.pk, target_table="vital_sign", target_record_id=reading.pk).exists())

    def test_staff_scope_and_csrf_are_enforced_for_workspace(self):
        url = self.workspace()
        self.assertEqual(self.client.get(url).status_code, 302)
        for account, status in ((self.admin, 403), (self.patient.patient, 403), (self.dentist.provider, 404)):
            self.client.force_login(account)
            self.assertEqual(self.client.get(url).status_code, status)
            self.assertEqual(self.client.post(url, {"action": "notes"}).status_code, status)
        secured = Client(enforce_csrf_checks=True)
        secured.force_login(self.physician.provider)
        self.assertEqual(secured.post(url, {"action": "notes"}).status_code, 403)
        self.assertContains(secured.get(url), self.previous.chief_complaint)

    def test_vitals_require_one_measurement_and_a_blood_pressure_pair(self):
        self.client.force_login(self.nurse.provider)
        data = {"action": "vitals", "vitals-expected_version": self.revision()}
        self.assertContains(self.client.post(self.workspace(), data), "Enter at least one recorded measurement")
        self.assertContains(self.client.post(self.workspace(), {**data, "vitals-systolic_mmhg": "120"}),
            "Enter both blood pressure readings together")
        self.assertContains(self.client.post(self.workspace(), {**data, "vitals-oxygen_saturation_pct": "101"}),
            "less than or equal to 100")
        self.assertFalse(self.visit.vital_signs.exists())

    def test_diagnosis_catalog_and_primary_selection(self):
        self.client.force_login(self.physician.provider)
        url = reverse("consultation:diagnosis_create")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        data = {"coding_system": "Prototype", "code": "ADDED", "description": "Fictional entry"}
        self.assertRedirects(self.client.post(url, data), reverse("consultation:diagnosis_list"))
        self.assertContains(self.client.post(url, data), "already exists")
        self.client.force_login(self.physician.provider)
        data = {"action": "notes", "notes-expected_version": self.revision(), "notes-diagnoses": [self.first.pk],
            "notes-primary_diagnosis": self.second.pk, "notes-chief_complaint": "Fictional"}
        self.assertContains(self.client.post(self.workspace(), data), "Select the primary diagnosis")
        self.assertContains(self.client.post(self.workspace(), {**data, "notes-diagnoses": [self.first.pk, self.first.pk]}),
            "Choose each diagnosis only once")
        self.assertFalse(self.visit.diagnoses.exists())
        selected = [self.first.pk, self.second.pk]
        self.assertRedirects(self.client.post(self.workspace(), {**data, "notes-diagnoses": selected}), self.workspace())
        self.assertEqual(self.visit.diagnoses.get(is_primary=True).diagnosis_id, self.second.pk)
        self.save_notes(diagnoses=selected, primary=self.first.pk)
        self.assertEqual(self.visit.diagnoses.get(is_primary=True).diagnosis_id, self.first.pk)
        self.save_notes(diagnoses=(self.second.pk,))
        self.assertEqual(list(self.visit.diagnoses.values_list("diagnosis_id", "is_primary")), [(self.second.pk, False)])

    def test_stale_note_forms_and_finalization_are_rejected(self):
        version = self.revision()
        self.save_notes()
        self.client.force_login(self.physician.provider)
        data = {"action": "notes", "notes-expected_version": version, "notes-chief_complaint": "Stale overwrite"}
        self.assertContains(self.client.post(self.workspace(), data), "This encounter changed")
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.chief_complaint, self.notes["chief_complaint"])
        review_version = self.revision()
        record_vitals(actor=self.nurse.provider, record_id=self.visit.pk, expected_version=review_version,
            measurements={"pulse_bpm": 75})
        with self.assertRaisesMessage(ValidationError, "This encounter changed"):
            finalize_consultation(actor=self.physician.provider, record_id=self.visit.pk, expected_version=review_version)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, "Draft")

    def test_reassignment_revokes_prior_attending_write_access(self):
        version = self.revision()
        assign_encounter(actor=self.admin, record_id=self.visit.pk, provider_id=self.dentist.pk,
            expected_provider_id=self.physician.pk)
        with self.assertRaises(PermissionDenied):
            save_consultation(actor=self.physician.provider, record_id=self.visit.pk, expected_version=version,
                notes=self.notes, diagnosis_ids=())

    def test_explicit_finalization_needs_saved_notes_without_forcing_vitals_or_diagnosis(self):
        self.client.force_login(self.physician.provider)
        url = self.workspace()
        data = {"action": "finalize", "finalize-expected_version": self.revision(), "finalize-confirm": "on"}
        self.assertContains(self.client.post(url, data), "Record the chief complaint")
        self.save_notes()
        data["finalize-expected_version"] = self.revision()
        self.assertContains(self.client.post(url, {**data, "finalize-confirm": ""}), "This field is required")
        self.assertRedirects(self.client.post(url, data), url)
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, "Finalized")
        self.assertIsNotNone(self.visit.finalized_at)
        self.assertFalse(self.visit.diagnoses.exists())
        self.assertFalse(self.visit.vital_signs.exists())
        result = self.client.get(url)
        self.assertContains(result, "Fictional follow-up plan")
        self.assertNotContains(result, "Save draft")
        self.assertEqual(self.client.post(url, data).status_code, 403)
        self.assertContains(self.client.get(reverse("consultation:list"), {"view": "finalized"}), url)
        self.client.force_login(self.nurse.provider)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_completion_and_audit_are_atomic_for_scheduled_encounter(self):
        appointment = Appointment.objects.create(patient=self.patient, slot=self.slot,
            status="Checked-In", reason_for_visit="Fictional")
        visit = open_scheduled_encounter(actor=self.admin, appointment_id=appointment.pk, provider_id=self.physician.pk)
        self.save_notes(visit)
        arguments = {"actor": self.physician.provider, "record_id": visit.pk, "expected_version": self.revision(visit)}
        with patch("apps.clinical.consultation._audit", side_effect=[None, ValidationError("Audit unavailable")]):
            with self.assertRaisesMessage(ValidationError, "Audit unavailable"):
                finalize_consultation(**arguments)
        appointment.refresh_from_db()
        visit.refresh_from_db()
        self.assertEqual((appointment.status, visit.status), ("Checked-In", "Draft"))
        finalize_consultation(**arguments)
        appointment.refresh_from_db()
        visit.refresh_from_db()
        self.assertEqual((appointment.status, visit.status), ("Completed", "Finalized"))
        self.assertEqual(AuditLog.objects.filter(actor_user_id=self.physician.pk, action_performed__in=(
            "Consultation finalized", "Appointment completed by finalization",
        )).count(), 2)

    def test_cannot_finalize_a_visit_on_your_own_patient_profile(self):
        patient = Patient.objects.create(patient=self.physician.provider, affiliation="Faculty")
        visit = MedicalRecord.objects.create(patient=patient, provider=self.physician)
        self.client.force_login(self.physician.provider)
        self.assertEqual(self.client.get(self.workspace(visit)).status_code, 404)
        with self.assertRaises(PermissionDenied):
            finalize_consultation(actor=self.physician.provider, record_id=visit.pk, expected_version=self.revision(visit))

    def test_database_protects_finalized_children_and_referenced_diagnosis_meaning(self):
        self.save_notes(diagnoses=(self.first.pk,), primary=self.first.pk)
        record_vitals(actor=self.nurse.provider, record_id=self.visit.pk, expected_version=self.revision(),
            measurements={"pulse_bpm": 75})
        referral = Referral.objects.create(record=self.visit, referred_by_provider=self.physician,
            destination="Fictional destination", reason="Fictional referral")
        finalize_consultation(actor=self.physician.provider, record_id=self.visit.pk, expected_version=self.revision())
        vital = self.visit.vital_signs.get()
        link = self.visit.diagnoses.get()
        rejected = (
            lambda: VitalSign.objects.bulk_create([VitalSign(record=self.visit, recorded_by_user=self.nurse.provider, pulse_bpm=76)]),
            lambda: VitalSign.objects.filter(pk=vital.pk).update(pulse_bpm=77),
            lambda: VitalSign.objects.filter(pk=vital.pk).delete(),
            lambda: RecordDiagnosis.objects.filter(pk=link.pk).update(record=self.previous),
            lambda: RecordDiagnosis.objects.filter(pk=link.pk).delete(),
            lambda: Diagnosis.objects.filter(pk=self.first.pk).update(description="Rewritten diagnosis"),
            lambda: Referral.objects.filter(pk=referral.pk).update(reason="Rewritten referral"),
            lambda: MedicalRecord.objects.filter(pk=self.previous.pk).delete(),
        )
        for mutation in rejected:
            with self.assertRaises(IntegrityError), transaction.atomic():
                mutation()
        Referral.objects.filter(pk=referral.pk).update(status=Referral.Status.COMPLETED)
        referral.refresh_from_db()
        self.assertEqual((referral.status, referral.reason), ("Completed", "Fictional referral"))
