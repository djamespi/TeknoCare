# ERD model implementation

The ERD's 22 entities now have Django models and migration source, organized by feature. Applying these migrations to the configured database is a separate deployment step; the hosted database has not been changed by this implementation task.

## Feature ownership

| Slice | Owned models | Scope |
| --- | --- | --- |
| `apps/register` | User | Existing authentication identity; registration composes patient/contact creation atomically. Keep `AUTH_USER_MODEL = 'register.User'`. |
| `apps/profile` | Profile (`user_profile`) | Contact/address details. Account names stay on User; birth date stays on Patient. |
| `apps/user_settings` | UserSettings | Account preferences. |
| `apps/university` | Department | University affiliation lookup. |
| `apps/patients` | Patient, EmergencyContact, PatientAllergy | Patient details and clinical intake. |
| `apps/providers` | Provider | Practitioner credentials and availability eligibility. |
| `apps/appointments` | ClinicRoom, Slot, Appointment | Scheduling/booking; transactional booking and cancellation services. |
| `apps/clinical` | MedicalRecord, VitalSign, Diagnosis, RecordDiagnosis, Referral | Encounters and observations. |
| `apps/prescriptions` | Medication, Prescription, PrescriptionItem | Medication catalog and prescription history. |
| `apps/billing` | AcademicTerm, StudentCharge | Tuition charge lines and verified posting/reversal acknowledgment services. |
| `apps/audit` | AuditLog | Append-only account/clinic action history. |

Each feature owns its models, migrations, tests, and services; future views/forms/URLs belong beside them. There is no shared repository/service abstraction or centralized clinic model file. Cross-feature FKs use lazy model labels; auth FKs use `settings.AUTH_USER_MODEL`. `apps/common` contains only a small validated-save primitive, PostgreSQL constraint adapters, and fictional test fixtures.

Services are application write boundaries, not authorization-complete HTTP endpoints. Booking locks the patient and slot to serialize overlapping requests. Charge services conservatively require an active Admin account and write audit events. Call them only after an authenticated view has checked access to the target objects. No finance API or payment gateway has been implemented.

## Deliberate schema adjustments

- Django 4.2 has no composite-primary-key model support. `RecordDiagnosis` has `record_diagnosis_id` plus UNIQUE `(record_id, diagnosis_id)`. Both this and one-primary-diagnosis-per-visit constraints are enforced. The regenerated ERD reflects this.
- Patient affiliation, historical visit affiliation, and slot room are nullable so old records can be migrated without fabricating eligibility or room assignments. New patient/visit saves require affiliation, direct insert guards verify visit snapshots, and an active slot must have an active room and verified provider. Old slots migrate inactive; verify and reactivate them deliberately. Unverified data cannot be charged.
- New provider designation defaults to `Unverified`; it is not a license or inferred clinical role. Review existing providers before scheduling them.
- Prescription `issued_at` is nullable for Draft prescriptions and required for Issued prescriptions. Do not invent an issue timestamp when creating a draft.
- Old cancellations retain an unknown NULL cancellation time. New normal cancellation writes require a timestamp; no fake historical cancellation time is backfilled.
- `currency_code` uses Django's `varchar(3)`. Configure `CLINIC_CURRENCY_CODE` (default `PHP`) before using billing. Decimal amounts are stored as historical line values. No tuition balance or payment status is stored.
- Newly added creation timestamps on legacy accounts/patients/appointments record migration time, not independently established original creation times. Existing medical-record visit timestamps are preserved exactly.

## Validation and database protection

Normal feature-model saves run `full_clean()` in a transaction. Updates lock their row. Date ranges, statuses, quantities, vital-sign values, partial uniqueness, and other row-local invariants use Django database constraints in addition to model validation.

PostgreSQL `btree_gist` plus range exclusion constraints reject overlapping active provider/room availability, including bulk inserts. The SQLite test adapter intentionally skips only these PostgreSQL-specific exclusions; its model validation is not proof of concurrent PostgreSQL behavior.

The billing guard migration installs database triggers on PostgreSQL and SQLite for student-only charges, initial status/creator/term eligibility, finalization before posting, immutable charge identity and posted/voided history, visit snapshot/appointment consistency, billed university-ID preservation, and append-only audit history. Direct/bulk writes cannot bypass these guards. Posting/reversal timestamp and reference combinations are CHECK constraints. PostgreSQL trigger execution still requires staging verification.

Some rules remain application boundaries: normal prescription saves preserve issued items/formulations, but unrestricted SQL/bulk operations can bypass those model methods. Granular staff permissions, a controlled clinical amendment workflow, complete role/profile consistency, self-access restrictions, all appointment state transitions, and external finance idempotency/reconciliation need the forthcoming feature workflows and database access policy. The model layer is not a claim that the clinic is fully operational.

When adding future SQLite schema migrations to tables referenced by the guards, remove/reinstall affected triggers around table rebuilds. PostgreSQL deployment needs permission to create `btree_gist` and trigger functions.

## Data-preserving migration path

1. The original migrations remain unchanged. New slice adoption migrations move Django's model state while retaining the same physical patient/provider/appointment/record/audit tables and primary keys.
2. Audit actors are remapped from Admin's shared user key to User before retiring the old Admin state.
3. `register.0002_move_clinic_features` checks appointment/provider consistency, snapshots old patient/provider/appointment/medical-record/profile/settings rows into `legacy_*` tables, and renames old admin/support tables to `legacy_admin` and `legacy_support_ticket`. Retired data stays in the database, not in repository files. PostgreSQL archives have row-level security enabled and PUBLIC privileges revoked because snapshots do not inherit source policies. Review owner/service-role access in staging; snapshots contain the original health/contact information.
4. Feature migrations then change fields, move profile/settings primary keys to the user FK, and create the new tables/constraints. Unknown affiliation and historical clinical text remain available for verified reconciliation rather than being guessed. Patient/contact names, diagnosis codes, dates of birth, and medicine doses are not parsed from ambiguous legacy text.
5. Existing admin access-level data is preserved in the legacy table. Clinic Admin now has explicit operational service permissions, not unrestricted Django superuser editing or automatic clinical powers; review the [access policy](../access_policy.md) before granting access to former Standard accounts. Retired support/admin tables and other archives are not active Django models.
6. The archival migration is intentionally irreversible through `migrate` because reconstructing a changed clinical database by guessing is unsafe. Rollback uses a verified database backup. Do not delete migration history or fake migrations to avoid this upgrade.

The update was tested on fresh and populated in-memory SQLite databases. Before deploying to the configured Supabase/PostgreSQL database: take and verify a backup, rehearse the full upgrade on a staging copy, review archived/unverified records and access policies, then apply migrations with the expected database privileges. No production migration has been run here.

## Verification commands

Step 1 adds isolated settings and a repeatable runner. See the project `README.md`
for local startup; tests do not need `.env` or a Supabase connection:

```powershell
.\venv\Scripts\python.exe scripts\check_project.py
```

These scripts force an in-memory SQLite connection regardless of the configured database URL:

```powershell
.\venv\Scripts\python.exe scripts\verify_erd_upgrade.py
.\venv\Scripts\python.exe scripts\verify_erd_models.py
```

Run the test suite on a disposable PostgreSQL database in staging to exercise its range exclusions and trigger implementation. The PostgreSQL-only test is skipped on SQLite.

The runtime is now Django 5.2 LTS. A replacement migration,
`profile.0003_profile_upgrade_compat`, performs non-key field changes before the
original ID removal/user-key promotion. This avoids an intermediate-primary-key
failure when rebuilding a populated SQLite profile table under Django 5.2, while
reaching the same final schema. The original migration is retained unchanged;
Django recognizes databases where it was already applied and does not rerun its
replacement's schema operations. The populated-upgrade script covers both paths.
No ERD columns or relationships change, and this is not a hosted migration result.

## Existing interface integration and evidence

Step 2 adds `register.0004_normalized_identity_uniqueness`: unique expression
indexes on `TRIM(school_id)` and `LOWER(TRIM(email))` strengthen existing identity
uniqueness without changing any ERD column, entity or FK. Diagram rerendering is
not needed for these indexes. A preflight rejects ambiguous existing identities
without rewriting/merging data. Tests cover rejection and preservation, bulk-write
duplicates, and populated legacy upgrade. PostgreSQL collation/whitespace behavior
and real legacy conflicts must still be reviewed in staging before hosted migration.
The old full-admin permission assumption is superseded by the access policy.

Registration now saves structured emergency contacts in one transaction with User/Patient creation. The public flow remains Student registration; staff intake must verify university membership before opening a visit or charging it. The profile form now edits phone/address/bio; names remain on User, and the Patient birth date replaces the old duplicate age field. Old display names/ages remain in the migration snapshot.

Step 0 removed the completed SQL JOIN assessment app, page and commands. Its
documents are retained under [the historical archive](../archive/sql_joins/README.md).
The clinic models/table names and any existing fictional sample rows are unchanged.
Do not re-seed or delete assessment records as part of ordinary clinic validation;
future sample cleanup requires exact ID/email matching and dependency review.

Commit and push after checks and student review. The user personally checks the
running registration/profile screens after a database upgrade and confirms in
chat. No Computer Use or screenshots are required under the current preference.
Keep `BASELINE_COMMIT.txt` unchanged and preserve Git history for the school project.
