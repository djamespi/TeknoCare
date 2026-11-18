from datetime import date
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from apps.common.test_data import clinic_data
from apps.clinical.models import MedicalRecord
from apps.patients.models import Patient
from .models import AcademicTerm, StudentCharge
from .services import record_posting, void_charge


class TuitionChargeTests(TestCase):
    def setUp(self):
        self.admin, self.patient, self.provider, self.slot, self.record = clinic_data()
        self.term = AcademicTerm.objects.create(academic_year="2026-2027", semester="First", start_date=date(2026, 8, 1), end_date=date(2026, 12, 31), is_open_for_charges=True)

    def new_charge(self, **kwargs):
        values = dict(record=self.record, term=self.term, created_by_user=self.admin, description="Fictional clinic service", amount=Decimal("100.00"), currency_code=settings.CLINIC_CURRENCY_CODE)
        values.update(kwargs)
        return StudentCharge(**values)

    def test_student_posting_acknowledgment_is_idempotent(self):
        charge = self.new_charge(); charge.save()
        first = record_posting(charge_id=charge.pk, billing_reference="TEST-REF", actor=self.admin)
        second = record_posting(charge_id=charge.pk, billing_reference="TEST-REF", actor=self.admin)
        self.assertEqual(first.posted_at, second.posted_at)
        self.assertEqual(StudentCharge.objects.count(), 1)
        self.assertEqual(self.admin.audit_events.count(), 1)

    def test_database_rejects_charges_for_each_personnel_type(self):
        for affiliation in ("Faculty", "Staff"):
            with self.subTest(affiliation=affiliation):
                Patient.objects.filter(pk=self.patient.pk).update(affiliation=affiliation)
                self.patient.refresh_from_db()
                visit = MedicalRecord.objects.create(patient=self.patient, provider=self.provider, chief_complaint="Fictional personnel visit")
                with self.assertRaises(IntegrityError), transaction.atomic():
                    StudentCharge.objects.bulk_create([self.new_charge(record=visit)])

    def test_affiliation_change_keeps_historical_eligibility(self):
        Patient.objects.filter(pk=self.patient.pk).update(affiliation="Staff")
        charge = self.new_charge(); charge.save()
        self.assertEqual(charge.record.affiliation_at_visit, "Student")

    def test_posted_amount_cannot_be_changed_by_bulk_update(self):
        charge = self.new_charge(); charge.save()
        record_posting(charge_id=charge.pk, billing_reference="TEST-REF", actor=self.admin)
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudentCharge.objects.filter(pk=charge.pk).update(amount=Decimal("200.00"))

    def test_posted_reversal_requires_confirmation_and_survives_term_closure(self):
        charge = self.new_charge(); charge.save()
        record_posting(charge_id=charge.pk, billing_reference="TEST-REF", actor=self.admin)
        with self.assertRaises(ValidationError):
            void_charge(charge_id=charge.pk, reason="Correction", actor=self.admin)
        self.term.is_open_for_charges = False; self.term.save()
        result = void_charge(charge_id=charge.pk, reason="Correction", reversal_reference="TEST-REV", actor=self.admin)
        self.assertEqual(result.status, "Voided")
        self.assertEqual(result.billing_reference, "TEST-REF")

    def test_closed_term_rejects_pending_charge_even_on_bulk_write(self):
        self.term.is_open_for_charges = False; self.term.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudentCharge.objects.bulk_create([self.new_charge()])

    def test_pending_can_be_voided_without_posting(self):
        charge = self.new_charge(); charge.save()
        result = void_charge(charge_id=charge.pk, reason="Duplicate", actor=self.admin)
        self.assertIsNone(result.posted_at)
        self.assertEqual(result.status, "Voided")

    def test_charge_deletion_is_blocked_for_bulk_and_normal_writes(self):
        charge = self.new_charge(); charge.save()
        with self.assertRaises(ValidationError): charge.delete()
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudentCharge.objects.filter(pk=charge.pk).delete()

    def test_zero_charge_rejected_at_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudentCharge.objects.bulk_create([self.new_charge(amount=0)])

    def test_non_admin_cannot_acknowledge_posting(self):
        charge = self.new_charge(); charge.save()
        with self.assertRaises(PermissionDenied):
            record_posting(charge_id=charge.pk, billing_reference="TEST-REF", actor=self.patient.patient)

    def test_posting_requires_finalized_record(self):
        draft = MedicalRecord.objects.create(patient=self.patient, provider=self.provider, chief_complaint="Fictional draft")
        charge = self.new_charge(record=draft); charge.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudentCharge.objects.filter(pk=charge.pk).update(status="Posted", billing_reference="TEST", posted_at=timezone.now())
