# TeknoCare project guide

Updated for clinic reference administration on November 18, 2026. Check Git status
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
| common | Small abstract validated-save and PostgreSQL constraint primitives |

Use lazy model labels for cross-feature FKs and `settings.AUTH_USER_MODEL` for
account relations. Import actual models from their owning slice, not registration
aliases. Keep dependencies one-way; do not add generic repository layers.

## Identity and clinic rules

`AUTH_USER_MODEL = 'register.User'` remains stable. This is a custom models.Model
account, not AbstractUser: PK user_id; login school_id; names fname/lname;
password hashes in password_hash. Use its password and session-hash APIs.
Roles are Admin/Patient/Provider; Active/Suspended status governs authentication.
Clinic Admin is not a Django superuser. Django admin is limited to read-only
account/display-profile/preferences inspection and must never expose password
hashes. Use `apps/common/permissions.py` at feature service boundaries; reload and
scope targets, not just navigation links. See `docs/access_policy.md` for the
role/action matrix. Admin status alone does not grant clinical authority.
Public registration is Student only; personnel/provider subtype provisioning uses
the atomic services in `apps/register/services.py`. Providers start inactive.
Preserve ID case and leading zeros; trim IDs and trim/lowercase emails. No official
ID format/domain or verified university identity is assumed. The normalized unique
indexes reject legacy collisions without rewriting identities; reconcile privately
before any migration that fails preflight. Never fake migrations to bypass it.

Patient profiles may coexist with Admin/Provider account roles so personnel can
receive care. Affiliation is Student/Faculty/Staff, separately from account role.
Old unknown affiliation is NULL and must be reviewed; never assume it is billable.
Faculty/Staff care is free. Student charges post to tuition; Posted does not mean
paid. Currency is configured by CLINIC_CURRENCY_CODE (default PHP). No direct
payment or university finance integration exists yet.

Password change and Admin-assisted non-Admin resets invoke validators and audit
without logging credentials. Never reset self/other Admin accounts through the
assistance page; use own password change or trusted operator recovery. No reset
email or mandatory next-login change is implemented. Suspension must use the
account-status service to revoke database sessions. Authentication denies missing
required Patient/Provider profiles and suspended accounts on every session lookup.
POST+CSRF protects mutations; GET profile/settings must not create rows. Keep
booking/cancellation/billing actor checks when building later feature pages.

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
limits, manual visual-review instructions, exact Git staging/commit/push commands for
the actual changed files and branch, and a suggested commit message. The user
reviews, commits, and pushes; do not perform those Git writes unless explicitly
asked. Update roadmap progress and decisions as features are completed.
For every future development step, give two or three main browser checks and
start each with the exact account type to sign in with. Include exact local
verification commands and browser actions
with expected results so the user can confirm it works before committing. State
what is still unverified and await the user's visual confirmation. Do not use
Computer Use, browser UI automation, or request/capture screenshots. The user
personally checks the visuals without screenshots. Continue appropriate CLI and
HTTP checks, and distinguish those results from user-confirmed visual review.
Use `git --no-pager diff`
in handoff commands to avoid trapping the user in Git's pager. See `README.md` for
the Step 1 confirmation checklist and `docs/supabase_migration_checklist.md` for
the separate hosted database gate. The user normally activates the venv; use
`python` in user-facing commands, and the explicit venv interpreter in tool calls
when needed. Step 0's completed removal is recorded in `docs/step_0_verification.md`.
Preserve the original profile migration alongside its Django 5.2-compatible
replacement; do not delete or rewrite either migration as routine cleanup.
Step 2's access policy and manual/Git handoff are in `docs/access_policy.md` and
`docs/step_2_verification.md`. New pages still require the user's visual approval.

## Interface and evidence workflow

Templates live in templates/<feature>, assets in static/css and static/js by
feature. Preserve the existing dark blue-green/teal style and account navigation.
Registration now collects a structured emergency contact; profile edits phone,
address and bio. Names stay on User and birth date stays on Patient.

All clinic pages extend `templates/base.html`; reuse shared navigation, messages
and `includes/form_fields.html` instead of duplicating page shells or form errors.
`static/css/includes/site.css` owns theme tokens, navigation, forms, tables and
pagination. Consume its variables in feature styles; do not restore the retired
duplicate CSS/import chains or obsolete per-page focus/animation scripts.
The appearance context processor reads the signed-in user's saved preference
without creating rows on GET; signed-out pages are light. Django admin retains
its own framework theme. Email delivery is unavailable even with its preference
enabled. Keep dashboard data own-account scoped and link only implemented,
authorized features, never invented metrics or unfinished clinic endpoints.
Use the shared table/empty/pagination patterns in `docs/interface_patterns.md` for
later lists. Step 3's manual/Git handoff is `docs/step_3_verification.md`; visual
review was confirmed by the user before Step 4. Each new step still requires its
own manual confirmation, without screenshots.

Step 4's `/clinic/` pages are Active-Admin-only, including GETs; use the feature
services rather than ModelForm.save or unrestricted admin editing. Shared list/
form shells are under templates/includes; common/web.py contains small permission,
filter and form-error helpers, not a generic repository. New provisioning uses
Step 2 account services and never accepts role/activation injection. Providers
start inactive; explicit manual-review confirmation is required for activation or
designation changes, without claiming external credential verification. Licenses
remain optional/NULL. Clinical and account status are separate.
Reference edits preserve history: protect referenced department codes, room
locations, known provider designations and charged term identity/calendar. Room/
provider deactivation blocks live work then disables future slots, never deletes
history; reactivation does not reopen slots. Account suspension revokes access
without canceling unresolved bookings. See docs/access_policy.md for exact rules.
Booking locks provider account, provider, room and slot after the patient lock;
future slot writers must use compatible ordering and fresh eligibility checks.
Do not reintroduce FOR UPDATE over a nullable outer join. Normal new active slots/
encounters use providers/eligibility.py to reject stale account/provider state.
No new schema change is needed for Step 4; PostgreSQL concurrency/hosted rehearsal
is still separate. See docs/step_4_verification.md for manual checks and Git handoff.

After each meaningful repository change, provide a short manual checklist of
pages/actions and expected outcomes, including desktop/narrow layout checks when
relevant. The user checks visuals and confirms in chat; screenshots are not
required. Do not mark visual review passed until the user confirms. Older capture
instructions in historical evidence documents are superseded by this preference.
Provide Git commands after review; preserve BASELINE_COMMIT.txt unchanged.

## Retired assessment material

Step 0 removed the completed SQL JOIN demo from the application. Its documents
are historical material under `docs/archive/sql_joins/`; do not follow their old
startup/seed instructions or restore the demo during clinic work. Preserve the
clinic models/tables, migrations, legacy archives and baseline evidence. Existing
fictional JOIN-DEMO rows were not deleted. Any future data cleanup must first
report exact reserved ID/email matches and dependencies and receive its own review;
never delete by name or prefix alone. Keep remaining known assessment fixtures
out of operational reports when those reports are implemented.
