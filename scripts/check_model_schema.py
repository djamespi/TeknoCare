"""Verify the clinic data model against its stable schema contract."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_test"
import django
django.setup()
from django.apps import apps
from django.db import models


# Key flags, column name, logical type, nullability
SCHEMA = """
[department]
PK | department_id | integer | NN
UQ | code | varchar(20) | NN
 | name | varchar(120) | NN
 | is_active | boolean | NN

[user]
PK | user_id | integer | NN
UQ | school_id | varchar(20) | NN
 | fname | varchar(50) | NN
 | lname | varchar(50) | NN
UQ | email | varchar(100) | NN
 | password_hash | varchar(255) | NN
 | user_type | varchar(10) | NN
 | account_status | varchar(10) | NN
 | created_at | timestamptz | NN

[patient]
PK,FK | patient_id | integer | NN
FK | department_id | integer | NULL
 | affiliation | varchar(10) | NULL
 | date_of_birth | date | NULL
 | medical_history_summary | text | NULL
 | created_at | timestamptz | NN

[provider]
PK,FK | provider_id | integer | NN
 | provider_type | varchar(20) | NN
UQ | license_number | varchar(50) | NULL
 | specialization | varchar(100) | NULL
 | is_active | boolean | NN

[user_profile]
PK,FK | user_id | integer | NN
 | phone_number | varchar(30) | NULL
 | home_address | text | NULL
 | bio | text | NULL

[user_settings]
PK,FK | user_id | integer | NN
 | dark_mode | boolean | NN
 | email_notifications | boolean | NN

[emergency_contact]
PK | contact_id | integer | NN
FK | patient_id | integer | NN
 | full_name | varchar(150) | NN
 | relationship | varchar(50) | NN
 | phone_number | varchar(30) | NN
 | is_primary | boolean | NN

[patient_allergy]
PK | allergy_id | integer | NN
FK | patient_id | integer | NN
 | allergen | varchar(150) | NN
 | reaction | text | NULL
 | severity | varchar(15) | NN
 | recorded_at | timestamptz | NN

[clinic_room]
PK | room_id | integer | NN
 | campus | varchar(100) | NN
 | building | varchar(100) | NN
 | room_number | varchar(20) | NN
 | is_active | boolean | NN

[slot]
PK | slot_id | integer | NN
FK | provider_id | integer | NN
FK | room_id | integer | NULL
 | start_time | timestamptz | NN
 | end_time | timestamptz | NN
 | is_active | boolean | NN

[appointment]
PK | appointment_id | integer | NN
FK | patient_id | integer | NN
FK | slot_id | integer | NN
 | reason_for_visit | text | NN
 | status | varchar(12) | NN
 | created_at | timestamptz | NN
 | canceled_at | timestamptz | NULL

[medical_record]
PK | record_id | integer | NN
FK,UQ | appointment_id | integer | NULL
FK | patient_id | integer | NN
FK | provider_id | integer | NN
 | chief_complaint | text | NN
 | affiliation_at_visit | varchar(10) | NULL
 | symptoms | text | NULL
 | examination_notes | text | NULL
 | treatment_plan | text | NULL
 | status | varchar(10) | NN
 | visited_at | timestamptz | NN
 | finalized_at | timestamptz | NULL

[vital_sign]
PK | vital_id | integer | NN
FK | record_id | integer | NN
FK | recorded_by_user_id | integer | NN
 | recorded_at | timestamptz | NN
 | temperature_c | numeric(4,1) | NULL
 | systolic_mmhg | smallint | NULL
 | diastolic_mmhg | smallint | NULL
 | pulse_bpm | smallint | NULL
 | respiratory_rate | smallint | NULL
 | oxygen_saturation_pct | numeric(5,2) | NULL
 | height_cm | numeric(5,2) | NULL
 | weight_kg | numeric(6,2) | NULL

[diagnosis]
PK | diagnosis_id | integer | NN
 | code | varchar(20) | NN
 | description | varchar(255) | NN
 | coding_system | varchar(30) | NN

[record_diagnosis]
PK | record_diagnosis_id | integer | NN
FK | record_id | integer | NN
FK | diagnosis_id | integer | NN
 | is_primary | boolean | NN
 | notes | text | NULL

[medication]
PK | medication_id | integer | NN
UQ | medication_code | varchar(30) | NN
 | generic_name | varchar(150) | NN
 | strength | varchar(50) | NN
 | dosage_form | varchar(50) | NN
 | is_active | boolean | NN

[prescription]
PK | prescription_id | integer | NN
FK | record_id | integer | NN
FK | prescriber_id | integer | NN
 | issued_at | timestamptz | NULL
 | status | varchar(10) | NN

[prescription_item]
PK | item_id | integer | NN
FK | prescription_id | integer | NN
FK | medication_id | integer | NN
 | dose | varchar(100) | NN
 | route | varchar(50) | NN
 | frequency | varchar(100) | NN
 | duration_days | smallint | NN
 | quantity | numeric(10,2) | NN
 | quantity_unit | varchar(30) | NN
 | instructions | text | NULL

[referral]
PK | referral_id | integer | NN
FK | record_id | integer | NN
FK | referred_by_provider_id | integer | NN
 | destination | varchar(200) | NN
 | reason | text | NN
 | status | varchar(12) | NN
 | referred_at | timestamptz | NN

[academic_term]
PK | term_id | integer | NN
 | academic_year | varchar(9) | NN
 | semester | varchar(20) | NN
 | start_date | date | NN
 | end_date | date | NN
 | is_open_for_charges | boolean | NN

[student_charge]
PK | charge_id | integer | NN
UQ | charge_code | varchar(40) | NN
FK | record_id | integer | NN
FK | term_id | integer | NN
FK | created_by_user_id | integer | NN
 | description | varchar(255) | NN
 | amount | numeric(12,2) | NN
 | currency_code | varchar(3) | NN
 | status | varchar(10) | NN
 | billing_reference | varchar(100) | NULL
 | reversal_reference | varchar(100) | NULL
 | created_at | timestamptz | NN
 | posted_at | timestamptz | NULL
 | voided_at | timestamptz | NULL
 | void_reason | text | NULL

[audit_log]
PK | log_id | integer | NN
FK | actor_user_id | integer | NULL
 | action_performed | varchar(100) | NN
 | target_table | varchar(50) | NN
 | target_record_id | integer | NN
 | logged_at | timestamptz | NN
"""

FOREIGN_KEYS = [
    ('patient', 'patient_id', 'user', 'user_id'),
    ('provider', 'provider_id', 'user', 'user_id'),
    ('user_profile', 'user_id', 'user', 'user_id'),
    ('user_settings', 'user_id', 'user', 'user_id'),
    ('patient', 'department_id', 'department', 'department_id'),
    ('emergency_contact', 'patient_id', 'patient', 'patient_id'),
    ('patient_allergy', 'patient_id', 'patient', 'patient_id'),
    ('slot', 'provider_id', 'provider', 'provider_id'),
    ('slot', 'room_id', 'clinic_room', 'room_id'),
    ('appointment', 'patient_id', 'patient', 'patient_id'),
    ('appointment', 'slot_id', 'slot', 'slot_id'),
    ('medical_record', 'appointment_id', 'appointment', 'appointment_id'),
    ('medical_record', 'patient_id', 'patient', 'patient_id'),
    ('medical_record', 'provider_id', 'provider', 'provider_id'),
    ('vital_sign', 'record_id', 'medical_record', 'record_id'),
    ('vital_sign', 'recorded_by_user_id', 'user', 'user_id'),
    ('record_diagnosis', 'record_id', 'medical_record', 'record_id'),
    ('record_diagnosis', 'diagnosis_id', 'diagnosis', 'diagnosis_id'),
    ('prescription', 'record_id', 'medical_record', 'record_id'),
    ('prescription', 'prescriber_id', 'provider', 'provider_id'),
    ('prescription_item', 'prescription_id', 'prescription', 'prescription_id'),
    ('prescription_item', 'medication_id', 'medication', 'medication_id'),
    ('referral', 'record_id', 'medical_record', 'record_id'),
    ('referral', 'referred_by_provider_id', 'provider', 'provider_id'),
    ('audit_log', 'actor_user_id', 'user', 'user_id'),
    ('student_charge', 'record_id', 'medical_record', 'record_id'),
    ('student_charge', 'term_id', 'academic_term', 'term_id'),
    ('student_charge', 'created_by_user_id', 'user', 'user_id'),
]

COMPOSITE_UNIQUES = {
    'clinic_room': [('campus', 'building', 'room_number')],
    'diagnosis': [('coding_system', 'code')],
    'academic_term': [('academic_year', 'semester')],
    'record_diagnosis': [('record_id', 'diagnosis_id')],
}


def logical_type(field):
    if field.is_relation:
        return logical_type(field.target_field)
    if isinstance(field, models.CharField):
        return f"varchar({field.max_length})"
    if isinstance(field, models.TextField):
        return "text"
    if isinstance(field, models.BooleanField):
        return "boolean"
    if isinstance(field, models.DateTimeField):
        return "timestamptz"
    if isinstance(field, models.DateField):
        return "date"
    if isinstance(field, models.DecimalField):
        return f"numeric({field.max_digits},{field.decimal_places})"
    if isinstance(field, models.SmallIntegerField):
        return "smallint"
    if isinstance(field, models.IntegerField):
        return "integer"
    raise AssertionError(f"Unmapped field: {field}")


def check():
    registered = {model._meta.db_table: model for model in apps.get_models()}
    for block in SCHEMA.strip().split("\n\n"):
        header, *rows = block.splitlines()
        table = header.removeprefix("[").removesuffix("]")
        model = registered[table]
        columns = {field.column: field for field in model._meta.concrete_fields}
        expected = [tuple(part.strip() for part in row.split("|")) for row in rows]
        assert set(columns) == {row[1] for row in expected}, f"Column mismatch: {table}"
        for flags, column, field_type, nullability in expected:
            field = columns[column]
            label = f"{table}.{column}"
            assert logical_type(field) == field_type, f"Type mismatch: {label}"
            assert field.null == (nullability == "NULL"), f"Nullability mismatch: {label}"
            assert field.primary_key == ("PK" in flags), f"Primary key mismatch: {label}"
            assert bool(field.is_relation) == ("FK" in flags), f"Foreign key mismatch: {label}"
            if "UQ" in flags:
                assert field.unique, f"Unique mismatch: {label}"
        if table in COMPOSITE_UNIQUES:
            actual = {
                tuple(model._meta.get_field(field).column for field in item.fields)
                for item in model._meta.constraints
                if isinstance(item, models.UniqueConstraint) and item.condition is None
            }
            assert set(COMPOSITE_UNIQUES[table]) <= actual, f"Composite unique mismatch: {table}"
    for child, column, parent, target in FOREIGN_KEYS:
        field = next(field for field in registered[child]._meta.fields if field.column == column)
        assert field.related_model._meta.db_table == parent, f"Wrong foreign table: {child}.{column}"
        assert field.target_field.column == target, f"Wrong foreign column: {child}.{column}"
    print("PASS: the clinic model preserves its columns, types, nullability, keys, and foreign key targets.")


if __name__ == "__main__":
    check()
