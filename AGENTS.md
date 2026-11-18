# TeknoCare project guide

Updated for the local setup checkpoint on November 18, 2026. Check Git status
before editing. The configured hosted database has not been upgraded by this task.

## Architecture and stack

TeknoCare is a university clinic Django 5.2 LTS application with PostgreSQL/Supabase,
server-rendered templates, CSS, and vanilla JavaScript. Keep vertical feature
slices under `apps/<feature>/`: that feature owns its models, migrations, tests,
services, forms, views, and URLs. Avoid putting unrelated clinic models back in
registration. Read `docs/erd/model_implementation.md` for migration and validation
boundaries and `docs/erd/README.md` for the target clinic rules.

| Feature | Ownership |
| --- | --- |
| register | User identity and atomic public student registration |
| login, home | Session login and account dashboard |
| profile | Profile/contact details; table user_profile |
| user_settings | Preferences; table user_settings |
| university | Department |
| patients | Patient, EmergencyContact, PatientAllergy |
| providers | Provider |
| appointments | ClinicRoom, Slot, Appointment; booking/cancellation services |
| clinical | MedicalRecord, VitalSign, Diagnosis, RecordDiagnosis, Referral |
| prescriptions | Medication, Prescription, PrescriptionItem |
| billing | AcademicTerm, StudentCharge; finance acknowledgment services |
| audit | User-based, append-only AuditLog |
| joins | Read-only SQL JOIN learning feature and fictional data commands |
| common | Small abstract validated-save and PostgreSQL constraint primitives |

Use lazy model labels for cross-feature FKs and `settings.AUTH_USER_MODEL` for
account relations. Import actual models from their owning slice, not registration
aliases. Keep dependencies one-way; do not add generic repository layers.

## Identity and clinic rules

`AUTH_USER_MODEL = 'register.User'` remains stable. This is a custom models.Model
account, not AbstractUser: PK user_id; login school_id; names fname/lname;
password hashes in password_hash. Use its password and session-hash APIs.
Roles are Admin/Patient/Provider; Active/Suspended status governs authentication.
Admin accounts currently have full admin permissions; do not infer granular
finance/clinical authorization merely from FK existence.

Patient profiles may coexist with Admin/Provider account roles so personnel can
receive care. Affiliation is Student/Faculty/Staff, separately from account role.
Old unknown affiliation is NULL and must be reviewed; never assume it is billable.
Faculty/Staff care is free. Student charges post to tuition; Posted does not mean
paid. Currency is configured by CLINIC_CURRENCY_CODE (default PHP). No direct
payment or university finance integration exists yet.

Models/migrations cover all 22 ERD entities. Most clinical views and workflows
remain to be built. Normal feature saves validate, but bulk/raw SQL bypasses model
methods. Billing/visit/audit guards and row constraints cover documented database
invariants; prescription bulk writes still require a restricted workflow.

## Migrations and data

Keep models and migrations together; do not rewrite the original applied migration
files or change AUTH_USER_MODEL. Adoption migrations move state across apps while
preserving original physical tables/IDs. register.0002 archives retired columns
and renames retired admin/support tables. It is intentionally irreversible:
rollback uses a verified backup. Never drop legacy_* tables or overwrite archived
clinical/contact data as routine cleanup.

Unknown legacy patient/visit affiliation and room remain nullable; old slots are
inactive until verified. Original diagnoses, prescription notes, profile names/
ages, contacts and other retired values remain in legacy_* snapshots. Do not
invent birth dates, clinical codes, provider credentials, charges or historical
timestamps to fill missing data. Preserve BASELINE_COMMIT.txt unchanged.

Do not apply migrations to the configured hosted database without a verified
backup and PostgreSQL staging rehearsal. PostgreSQL needs btree_gist and trigger
privileges. SQLite tests intentionally skip PostgreSQL range exclusions. For future
SQLite table rebuild migrations, remove/reinstall affected SQL guard triggers.

## Checks

Use the existing interpreter, without depending on shell activation. Local preview
uses `config.settings_local` (SQLite), tests use `config.settings_test` (in-memory
SQLite), and only explicit hosted/staging use loads `.env` via `config.settings`.
Local/test modules ignore `DATABASE_URL`. Never preview against hosted data by
accident. The repeatable check runner forces test settings in child processes:

```powershell
.\venv\Scripts\python.exe scripts\check_project.py
```

These two scripts also force test settings independently of the .env URL:

```powershell
.\venv\Scripts\python.exe scripts\verify_erd_upgrade.py
.\venv\Scripts\python.exe scripts\verify_erd_models.py
```

The upgrade script verifies populated old-schema data, not only fresh migrations.
The ERD checker verifies every model column/type/key/nullability/FK target against
the diagram source. Update the ERD and rerender assets when model schema changes.
Run PostgreSQL-specific tests on a disposable staging database before deployment.

## Development checkpoints

Follow `docs/development_plan.md` for the phased school-project prototype roadmap,
ERD boundaries, and unresolved university-policy assumptions. Implement only the
feature/step requested by the user; do not automatically implement the whole plan.
After every delivered change, provide behavior and validation results, remaining
limits, review/screenshot instructions, exact Git staging/commit/push commands for
the actual changed files and branch, and a suggested commit message. The user
reviews, commits, and pushes; do not perform those Git writes unless explicitly
asked. Update roadmap progress and decisions as features are completed.
For every future change, include exact verification commands and browser actions
with expected results so the user can confirm it works before committing. State
what is still unverified and what screenshots to capture. Use `git --no-pager diff`
in handoff commands to avoid trapping the user in Git's pager. See `README.md` for
the Step 1 confirmation checklist and `docs/supabase_migration_checklist.md` for
the separate hosted database gate. Step 0 remains pending; the user chose Step 1
first. Preserve the original profile migration alongside its Django 5.2-compatible
replacement; do not delete or rewrite either migration as routine cleanup.

## Interface and evidence workflow

Templates live in templates/<feature>, assets in static/css and static/js by
feature. Preserve the existing dark blue-green/teal style and account navigation.
Registration now collects a structured emergency contact; profile edits phone,
address and bio. Names stay on User and birth date stays on Patient.

After each meaningful repository change, tell the user whether to commit/push
and whether application screenshots are needed. Capture every created/modified
running interface in APPLICATION_SCREENSHOTS. Model source screenshots do not
replace application screenshots. Model-only changes need Git evidence; form or
screen changes need running application screenshots too. Collect GitHub history
screenshots for final submission. Keep BASELINE_COMMIT.txt unchanged.

## SQL JOIN learning feature

The user has completed the assessment and requested its removal in the roadmap.
Step 0 of `docs/development_plan.md` removes the demo app, route, navigation,
assets, commands and demo-only tests when that implementation step is requested.
Preserve clinic models/tables, migrations, legacy archives and baseline evidence;
hosted sample-data deletion is a separate reviewed action. Until removal, the
following rules govern the existing demo.

Keep queries read-only and parameterized, filtered to reserved fictional JOIN-DEMO
accounts/emails. The canonical patient/provider/slot/appointment table names stay
stable; scheduled provider is obtained through Slot. Seed data has unusable
passwords and suspended accounts; never overwrite mismatched existing records.
Migrated legacy samples may require review before re-seeding because their new
fields are intentionally unverified. Tests and verification commands cover the
2/1/0 sample appointment pattern. Existing SQL activity/video docs remain under
docs/. Never run seed commands against real records as part of verification.
