# TeknoCare: proposed university clinic ERD

Open [the PNG](teknocare_improved_erd.png) and zoom in to inspect columns and cardinalities. It is an 8,000-pixel diagram with 22 entities and 28 foreign-key relationships. [The SVG](teknocare_improved_erd.svg) is a scalable copy; [the data dictionary](data_dictionary.md) lists every column and FK target. [The design review](design_review.md) distinguishes schema coverage from operational readiness.

This is a **proposed design**, based on `BENITEZ_physicalERD.pdf` and the repository's current Django models. It does not describe an already implemented schema. No application models, migrations, or database records were changed. It uses PostgreSQL types to match the project's configured database.

The proposed ERD omits the separate `admin` and `support_ticket` entities. Django admin access does not require a clinic-specific admin-profile table, and a support-ticket workflow is outside the selected clinic scope. Keep `Admin` as a value in `user.user_type`: the current custom user's `is_staff` property uses that role. Django admin permissions and custom-user compatibility still need implementation review. The retained `audit_log` references any acting user, so it supports provider and other account actions without an admin entity.

## What improves the original ERD

| Area | Proposed improvement | Purpose |
| --- | --- | --- |
| University membership | `department`, patient affiliation | Distinguish Student, Faculty, and Staff patients and their university department. This is separate from account role. |
| Patient details | Date of birth, `emergency_contact`, `patient_allergy` | Support multiple contacts and structured allergy records. Derive age from birth date. |
| Account details | `user_profile`, `user_settings` | Include the profile and preferences already present in the application; keep names in `user`. |
| Availability | `clinic_room`, provider/room/time-based slots | Assign rooms per scheduled slot, rather than permanently attaching a room number to a provider. |
| Booking | Slot cancellation history and conditional uniqueness | Permit rebooking after cancellation while preventing two non-canceled bookings of one slot. Derive booking state instead of storing `is_booked`. |
| Walk-in care | Optional appointment on `medical_record` | A clinic visit can exist without a reservation; each record still has a patient and attending provider. |
| Clinical observations | `vital_sign` | Store multiple timestamped observations, with the user who recorded each set. Units are explicit in column names. |
| Diagnosis | `diagnosis` + `record_diagnosis` | Allow multiple diagnoses per visit and reuse catalog entries rather than storing one unstructured diagnosis field. |
| Treatment | `medication`, `prescription`, `prescription_item` | Separate a prescription from its individual medicines, doses, routes, quantities, and instructions. |
| Further care | `referral` | Record a referral destination, reason, referring provider, and status. |
| Tuition billing | `academic_term`, `student_charge` | Add student clinic charges to university billing; Faculty and Staff receive free care. |
| Historical eligibility | `medical_record.affiliation_at_visit` | Preserve Student/Faculty/Staff eligibility when a patient's current affiliation later changes. |
| Accountability | `audit_log.actor_user_id` | Record actions by providers and other users, as well as admins. System events can have no user actor. |

## How to read the relationships

- PK: primary key. FK: foreign key. UQ: single-column UNIQUE. NN: NOT NULL. NULL: optional.
- `1` at an end means exactly one; `0..1` means optional one; `0..*` means zero or more. Crow's feet denote many.
- Read both ends: each appointment has **one** patient; a patient can have **zero or many** appointments.
- Each account can have zero or one Patient row and zero or one Provider row. A provider or admin may also have a Patient row when receiving care. Account role controls the primary interface; affiliation controls billing eligibility.
- `record_diagnosis` has a **composite** primary key, `(record_id, diagnosis_id)`. Both are also foreign keys. This resolves the many-to-many visit/diagnosis relationship.
- A medical record has zero or one appointment, and an appointment has zero or one medical record. NULL appointment means a walk-in visit. PostgreSQL's ordinary nullable UNIQUE permits multiple walk-in records.
- A slot can have multiple historical appointments, but all except at most one must be canceled. This conditional rule needs an index in addition to the cardinality line.
- All 28 FK targets are explicit in the data dictionary. `audit_log.target_table` and `target_record_id` are descriptive event metadata, **not** foreign keys.
- A medical record has zero or many student charges; each charge belongs to one record and one academic term, and has one creating user. The patient is obtained through the medical record, without duplicating `patient_id` in the charge.

## Constraints to implement with the schema

These rules are part of the proposal. The PNG displays columns, keys, types, and cardinalities; it does not implement checks, triggers, authorization, or indexes.

### Identity and patient data

1. Use generated integer identity keys for non-FK primary keys. Shared subtype/profile/settings primary keys reference `user.user_id` and do not generate separate identities. Retain existing IDs during migration.
2. Keep `user_type IN ('Admin', 'Patient', 'Provider')` as the primary interface/access classification, with `account_status IN ('Active', 'Suspended')`. Patient-role accounts require a Patient row; Provider-role accounts require a Provider row. Allow Admin/Provider accounts to also have a Patient row when receiving care, without a second login. Only approved clinic practitioners receive Provider rows; Admin accounts may have one if independently qualified. Create required profiles transactionally and enforce these cross-table rules with deferred constraint triggers where needed. There is no separate Admin table. Profile and settings rows remain optional. The Admin role does not itself implement Django's full permissions API; clinical and billing permissions must be explicit.
3. `patient.affiliation IN ('Student', 'Faculty', 'Staff')`. Department is optional so registration need not fail when it is not yet known. Suggested provider types: Physician, Nurse, Dentist. These are clinic workflow categories, not prescribing permissions.
4. Keep account names only in `user.fname` and `user.lname`. Remove duplicated editable `Profile.full_name` after reviewing existing values. Replace stored age with optional `patient.date_of_birth`; reject future birth dates in form validation. Do not invent birth dates from ages.
5. Store only password hashes. Keep university IDs and emails unique, with an agreed normalization rule before enforcing uniqueness. Quote the existing PostgreSQL table name `"user"` in raw SQL.
6. At most one primary emergency contact per patient: partial unique index on `emergency_contact(patient_id) WHERE is_primary`. A patient may initially have no contact. Require one in the workflow if the clinic decides it is mandatory.
7. Suggested allergy severity values: Unknown, Mild, Moderate, Severe. No allergy rows means **not documented**, not a confirmed absence of allergies. Verify patient details before relying on them.

### Scheduling and encounters

1. `slot.end_time > slot.start_time`. Require active providers and rooms when creating or booking availability. Make `(campus, building, room_number)` unique in `clinic_room`.
2. Prevent overlapping active slots for the same provider and for the same room. In PostgreSQL, use separate GiST exclusion constraints with `tstzrange(start_time, end_time, '[)')`, equality on provider/room, and `WHERE (is_active)`; integer equality requires `btree_gist`. Half-open ranges allow adjacent slots.
3. Appointment statuses: Scheduled, Checked-In, Completed, Canceled, No Show. Create a **partial unique index** on `appointment(slot_id) WHERE status <> 'Canceled'`. This prevents a concurrent double booking and preserves cancellation history. Do not make `slot_id` globally UNIQUE. Populate `canceled_at` only for Canceled status; constrain the status and timestamp to agree.
4. Do not duplicate `appointment.provider_id`: obtain the scheduled provider through `appointment.slot_id -> slot.provider_id`. Avoid a separate `slot.is_booked` flag. Count no-shows from appointments instead of storing a counter that can drift.
5. Forbid overlapping live appointments for one patient through a transactionally serialized booking service (for example, lock the patient row before checking conflicts). A plain form validation query is insufficient under concurrent requests. This rule spans appointment and slot tables.
6. For a scheduled medical record, enforce `medical_record.patient_id = appointment.patient_id` with a database constraint trigger or equivalent transactionally enforced workflow. The record's provider is the **actual attending provider**, who can differ from the originally scheduled provider. A walk-in requires no artificial slot or appointment.
7. Medical record statuses: Draft and Finalized. Finalized requires `finalized_at`; Draft requires it to be NULL. Do not finalize a visit against a canceled or no-show appointment. Authorize finalization and subsequent amendments through the clinic workflow.
8. Slot times/provider and appointment patient/slot must not be edited after the appointment has a clinical record. Preserve the historical link; cancel and create a replacement booking where appropriate.
9. Use timezone-aware timestamps. Present the session and appointments in the university's local timezone, independently of timestamp storage. Set creation/recording timestamps server-side. Validate that end/finalization timestamps do not precede their corresponding start timestamps.

### Clinical records and prescriptions

1. Vital measurements are optional individually, but require at least one measurement per `vital_sign` row. Require positive values for recorded height, weight, pulse, respiratory rate, and blood pressure; oxygen saturation must be between 0 and 100. Record systolic and diastolic values together. Additional clinical validation belongs to the clinic's agreed workflow.
2. Restrict vital-sign recording to authorized clinic staff. A FK to `user` establishes who recorded the observation; it does not grant permission.
3. Diagnosis codes are unique within a coding system: composite UNIQUE `(coding_system, code)`. Enforce at most one primary diagnosis per record with a partial unique index on `record_diagnosis(record_id) WHERE is_primary`.
4. Prescription statuses: Draft, Issued, Canceled. An issued prescription requires at least one item. `quantity > 0` and `duration_days > 0`. Both the item quantity and its unit must be stored. Dose, route, and frequency are explicit text fields for the prescriber's instructions.
5. Restrict issuing prescriptions to authorized prescribers. `prescriber_id` must reference a provider, but a provider record by itself does not grant prescribing permission. The prescriber can differ from the attending provider, with authorization recorded in the audit trail.
6. Referral statuses: Pending, Completed, Canceled. The referring provider may differ from the attending provider when the workflow authorizes it.
7. Inventory, medicine dispensing, laboratory orders, immunization tracking, and uploaded medical certificates are **outside this version**. A medication catalog and prescription do not imply stock management or actual dispensing. Preserve the name, strength, and dosage form of medication rows already referenced by issued prescriptions; create a new catalog entry for a changed formulation. Finalized clinical notes and issued prescription items require controlled amendments rather than silent overwrites.

### Student charges posted to tuition

1. The clinic records amounts to add to tuition. It does **not** collect payments or store tuition balances. Posted means the university billing system has acknowledged the charge, not that the student has paid. Faculty and Staff visits create **no charge rows**, including zero-amount placeholders.
2. Capture `medical_record.affiliation_at_visit IN ('Student', 'Faculty', 'Staff')` from verified patient affiliation when opening the visit, server-side. Restrict later changes after finalization or charge creation. Permit a student charge only when its record's historical affiliation is Student. Use a database trigger and an authorized transactional service for this cross-table rule. This preserves historical billing when a student later becomes personnel. Corrections must review existing charges rather than silently changing eligibility.
3. `academic_term` is unique on `(academic_year, semester)`; require a valid year pair such as `2026-2027`, nonempty semester, and `end_date >= start_date`. Term dates refer to the academic calendar; the billing term may differ from the visit term under university policy. Require a term open for charges when adding a charge or submitting it for posting. Closing a term must not prevent a necessary audited reversal.
4. Each charge is one billable line with a stored amount and description. Multiple services or medicines can be separate lines for the same visit. Require `amount > 0`, a nonempty description, and one configured three-letter currency code throughout the clinic. Use decimal arithmetic, not floating point. Free student services have no charge. Prices are historical snapshots; do not recalculate existing charges from a changing price list.
5. Use a unique, immutable `charge_code` as the external posting idempotency key. Reuse that code when retrying the same posting. Require a finalized medical record before submitting a charge for posting. Only authorized clinic billing staff may create or post charges; do not let patients set their own affiliation, amount, term, or status. The original creating user is retained; later actions belong in the audit trail.
6. Allowed transitions: Pending -> Posted, Pending -> Voided, Posted -> Voided after confirmed reversal. No transition out of Voided. Pending has no billing/reversal reference or posting/void timestamp. Posted requires nonempty `billing_reference` and `posted_at`, and no void/reversal data. Every Voided row requires `voided_at` and a nonempty `void_reason`. A never-posted void retains NULL billing/posting/reversal fields. A previously posted void retains the original billing reference and posting time, and also requires a nonempty `reversal_reference`. Encode valid row combinations as CHECK constraints and enforce transitions/immutability with triggers and services.
7. Set timestamps server-side. Require `posted_at >= created_at` and `voided_at >= created_at` (and >= `posted_at` when present). A university statement reference may cover several charges, so `billing_reference` is not globally unique. Never mark a charge Posted merely because an export file was generated; record the university's acknowledgment or a verified manual posting reference.
8. Confirm the university supports idempotent posting or reconciliation by `charge_code`. An external call and a local database transaction are not atomic: use locking plus an export/reconciliation workflow so retries cannot add tuition charges twice. If an external reversal fails, keep the local charge Posted until reconciliation confirms reversal. Audit failed attempts without fabricating success.
9. Do not delete charges or alter their record, term, description, currency, amount, or code after posting. Void/reverse and create a corrected line with a new code. Protect referenced records, academic terms, and creating users from deletion. Prevent changing a medical record's patient or the related university ID while charges exist without an explicit reconciliation procedure. Index charges by `(term_id, status)` and `record_id`.
10. Finance integration, tuition payment settlement, receipts, balances, scholarships, and payment gateways remain the university billing system's responsibility. This proposal supports manual verified posting or an eventual integration; neither is implemented in the current app.

### Auditing and retention

1. Audit all relevant account, booking, and clinical actions. `actor_user_id` is nullable for system actions; write descriptive action codes. Do not place passwords, tokens, or full clinical notes in the audit log. A polymorphic target is metadata and cannot be enforced by one ordinary FK.
2. Treat audit records as append-only through database privileges and application permissions. An ERD alone cannot make them immutable.
3. Use PROTECT/RESTRICT for patient, provider, appointment, clinical, diagnosis, and medication references that already have dependent records. Prefer deactivation and cancellation over deletion. Avoid the original schema's broad cascading deletion of clinical history.
4. Account subtype/profile/settings rows can use CASCADE when an otherwise deletable account is removed; patient/provider dependencies must first block deletion. `audit_log.actor_user_id` can use SET NULL if account deletion is permitted; retain the event.
5. Index foreign-key columns used in joins and filters; PostgreSQL does not create child FK indexes automatically. Start with appointments by patient/status, slots by provider/start time, and records by patient/visited time. Choose further indexes using actual queries.

## Migration from the current project

The current implementation has nine core models in `apps/register/models.py`, plus `Profile` and `UserSettings` in their own apps. Implement this proposal in reviewed Django migrations, not by replacing the live database.

1. Add new tables and nullable columns first. Keep university IDs, user IDs, appointment IDs, and baseline evidence unchanged.
2. Map `profile_profile` to proposed `user_profile` and `user_settings_usersettings` to proposed `user_settings`, preserving data and unique user links. Both currently have separate implicit IDs; this proposal uses their user FK as the primary key. Stage that key change deliberately and verify dependent references. Review names/ages before retiring the old fields.
3. Convert the free-text emergency contact to structured contacts only where a name and phone can be established. Retain the original text until reviewed; do not guess missing details. Map provider rooms to lookup rows and assign rooms to slots. When implementing removal of the existing Admin and SupportTicket models, review dependencies and preserve any existing ticket/admin-specific data before dropping tables. Retain Admin user accounts and their role. Map existing audit actors through `admin_id` to the corresponding `user_id` before removing that FK; shared keys make this possible without inventing actors.
4. Preserve existing diagnosis and prescription notes until they can be reviewed and migrated into catalog/line-item records. Free text cannot be reliably split into diagnoses or medicine doses automatically.
5. Check existing appointment/provider/slot consistency before removing redundant `appointment.provider_id`. Remove the slot's global one-to-one appointment constraint only when the partial unique booking index is ready. Allow NULL on the medical-record appointment link for walk-ins.
6. Add checks, exclusion constraints, indexes, role rules, and retained-record deletion protections after resolving existing inconsistencies. Verify both PostgreSQL concurrency behavior and application validation.
7. Add academic terms and student charges without inventing historical fees. Backfill visit affiliation only from verified evidence; flag unknown legacy records for review rather than defaulting them to billable students. Ensure personnel with an Admin/Provider login can also receive care through a Patient row.
8. Build and test the new workflows in small commits. This diagram is design evidence; the instructor also requires screenshots of actual application screens created or modified during development.

## Regenerating the artifacts

`generate_erd.py` uses only the Python standard library and validates every FK target and key type before generating DOT and the data dictionary:

```powershell
.\venv\Scripts\python.exe docs\erd\generate_erd.py
```

With Graphviz installed separately:

```powershell
dot -Tsvg docs\erd\teknocare_improved_erd.dot -o docs\erd\teknocare_improved_erd.svg
```

Alternatively, install `@viz-js/viz` in a separate tooling directory and pass the absolute path to its `dist/viz.cjs` module:

```powershell
node docs\erd\render_erd.cjs PATH_TO_VIZ_MODULE
```

For PNG export, use Python with PyMuPDF available:

```powershell
python docs\erd\export_png.py
```

Rendering dependencies were installed in a temporary tooling folder for this export, not added to the application's requirements. The exporter checks the SVG's entity and FK sets against the generator before saving the PNG. The diagram was visually inspected after rendering. Structural validation is not a test of database constraints or the billing integration.
