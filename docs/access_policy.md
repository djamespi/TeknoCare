# Prototype account and access policy

Introduced in Step 2 and extended in Step 4, November 18, 2026. These are
conservative school-project rules, not confirmed CIT-University operating policy.
Admin reference/provisioning screens are available under `/clinic/`; clinical
screens remain later work. Never infer permission just from a visible link or a
related patient/provider row.

## Accounts and identity

- Public registration creates only an Active Patient account, a Student patient
  profile and one structured primary emergency contact in the same transaction.
  Posted role, affiliation, creator or status fields are not accepted.
- Admin-only services provision Faculty/Staff Patient accounts or Provider accounts
  with their required subtype. New providers start clinically inactive, with
  Unverified designation by default. Blank optional licenses become NULL; no license,
  provider ID format or university membership evidence is fabricated.
- An Admin or Provider can also have a Patient profile without changing their
  primary account role. Missing required Patient/Provider profiles deny login and
  existing sessions cleanly. A clinically inactive Provider can still use account
  pages; activation is separate from account status.
- IDs are trimmed strings: preserve case, punctuation and leading zeros. Emails
  are trimmed and lowercased. No official student/personnel/provider ID pattern or
  mandatory university email domain has been confirmed. No Supabase Auth/SSO or
  university registry validation is present.
- `register.0004_normalized_identity_uniqueness` adds unique expression indexes on
  SQL `TRIM(school_id)` and `LOWER(TRIM(email))`. It stops on existing collisions
  before creating indexes; it does not merge accounts or rewrite existing values.
  Review legacy non-ASCII/collation and unusual whitespace cases in PostgreSQL
  staging; SQL TRIM is not a general Unicode identity-normalization policy.
- The custom user remains `register.User`, with `password_hash` and session-hash
  APIs. Django password validators use the actual `school_id`, `fname`, `lname`
  and `email` fields. Forms and provisioning/password services invoke validation;
  low-level ORM managers/raw SQL are trusted maintenance interfaces, not safe
  public provisioning APIs. See Django's
  [password validation documentation](https://docs.djangoproject.com/en/5.2/topics/auth/passwords/#password-validation).

## Role/action matrix

Every action first reloads the actor's current Active account. Missing required
subtypes and unknown actions deny access. Clinical actions additionally need an
active Provider profile designated Physician, Dentist or Nurse.

| Action | Patient/owner | Physician/Dentist | Nurse | Admin without clinical designation |
| --- | --- | --- | --- | --- |
| Account/profile/preferences/password | Own account | Own account | Own account | Own account |
| Manage accounts, reference data, tuition charges, audit viewer, operational reports | No | No | No | Yes |
| Book appointment | Own Patient profile | Own Patient profile if present | Own Patient profile if present | Active Patient profile target |
| Cancel appointment | Own future Scheduled booking, no encounter | Same ownership rule | Same ownership rule | Same state rules, any patient |
| Manage provider availability | No | Own provider | Own provider | Any provider; scheduling validation still required |
| Patient operational details | Self | Assigned Draft encounter or live/current-or-future booking | Same assignment, or today's Draft triage queue | Operational access, not full clinical notes |
| Patient intake and identity/affiliation correction | No | No | No | Yes |
| Birth date and emergency contact changes | Own Patient profile | Own Patient profile if present | Own Patient profile if present | Own Patient profile if present |
| Structured allergy review and recording | Read own list | Review and record for patients under care. Read own list if present. | Same care scope plus today's Draft triage queue. Read own list if present. | Read own list if present. |
| Full clinical record access | No; own Finalized summary only | Assigned encounter; other Finalized history only while under care | No full-note access | No |
| Record vitals | No | Own assigned Draft encounter | Own assigned Draft or today's Draft triage | No |
| Finalize consultation / issue prescription | No | Own assigned Draft encounter | No | No |

Self-treatment is denied for vitals, finalization and prescribing. An Admin with
an active qualified Provider profile gains clinical authority through that profile,
not through Admin status. Issued/finalized immutability and later lifecycle guards
remain additional requirements; an action permission does not bypass them.

`patient.view` is an operational/patient-context permission, not authorization to
dump medical history. `record.view` permits only a restricted Finalized summary
for the owning patient; later patient-facing views must explicitly project safe
fields and exclude internal notes. Nurses receive a dedicated triage/vitals view,
not the full-record view. Those pages are not created in this step.

Helpers live in `apps/common/permissions.py`. Existing appointment booking,
cancellation and billing write services now require a canonical authorized actor
and audit successful writes transactionally. Booking rechecks provider, room,
slot and account activity. Future features must scope list/detail queries, lock
and reload mutable targets in write transactions, use these checks at the service
boundary, and test forged IDs and state transitions. A policy helper alone does
not secure an unfinished workflow or direct database access.

## Passwords, sessions and Admin recovery

- `/login/password/`: requires the current password, validates the new password,
  audits success without credentials, rotates the current session and keeps it
  signed in. Other sessions fail their authentication hash on next use, following
  Django's [session invalidation mechanism](https://docs.djangoproject.com/en/5.2/topics/auth/default/#session-invalidation-on-password-change).
- `/login/reset-password/`: Active Admin only, with their current password
  re-entered. Verify the fictional person's identity in person first. Only
  non-Admin targets are allowed; status/role do not change. Communicate the new
  password privately and ask the person to change it. No email is sent, and no
  forced-next-login password change or password-history tracking is implemented.
- Own/other Admin credentials cannot be reset through that assistance page. Use
  the own password page, or trusted server-operator recovery with Django's
  `changepassword` command against the explicitly intended database. This operator
  command is outside the application audit workflow and must not be exposed to
  ordinary clinic users. The local demo bootstrap is retained.
- `set_account_status` denies self/other Admin targeting and revokes that
  non-Admin user's unexpired database sessions when suspending them. Reactivation
  does not resurrect those sessions. Direct SQL status changes are not a substitute
  for this service; all authentication still denies accounts while Suspended.
  Step 4's Change account access page uses this service. Existing bookings/clinical
  history and the separate clinical activation flag are preserved; the clinic must
  follow up unresolved work. Suspended practitioners are ineligible for new slots,
  bookings and encounters regardless of a previously active clinical flag.
- Switching to the clinic authentication backend signs out sessions established
  with the previous backend. Sign in again after this update; do not fake/clear
  migration history to work around a sign-in problem.
- Login accepts safe same-host `next` destinations, rejects external redirects
  and avoids direct authentication-page loops. Mutating forms use POST and CSRF;
  GET profile/preferences requests no longer create database rows.

Clinic Admin is not a Django superuser. Django admin permits read-only inspection
of accounts, display profiles and preferences only. Account details exclude
password hashes; add/change/delete and auth group management are denied. Clinical
tables are not registered as unrestricted model editors. Future feature pages use
authorized services instead of re-enabling generic admin editing.

## Step 4 reference administration

All Clinic setup list/create/edit pages require an Active Admin, even for GETs.
They expose only operational reference/account information, not clinical notes.
Write services recheck the actor and whitelist data; POSTed primary keys, roles,
creators and clinical activation on account creation cannot override server values.
Lists search/filter with bound forms, paginate deterministically and escape data.
Mutation forms use CSRF, atomic writes/audit and friendly validation/race errors.
There are no delete actions or unrestricted Django-admin model editors.

- Departments preserve patient links; a referenced code cannot be changed.
  Inactive departments are unavailable for new personnel assignments. Affiliation
  never changes merely because its department is deactivated.
- Room location cannot be rewritten once any slot references it. Deactivation
  blocks on unresolved Scheduled/Checked-In bookings, including overdue ones;
  otherwise it disables active future slots and preserves all historical rows.
- Provider creation always starts clinically inactive. Existing Admin/Provider
  accounts without a Provider profile can receive an inactive Unverified profile,
  preserving the primary role, password and any secondary Patient profile.
  Activation or designation change requires a fresh manual-review confirmation.
  Activation also requires a known designation and Active Admin/Provider account.
  This checkbox is a prototype attestation recorded in audit, not external license
  verification or stored documentary proof. License remains optional/NULL.
- Referenced known provider designations are protected from silent changes.
  Legacy Unverified designation can be reconciled with explicit review. Clinical
  deactivation blocks on live bookings or Draft attending encounters; otherwise
  future active slots are disabled, not deleted. Reactivation of a room/provider
  does not reopen availability. Account suspension remains available to revoke
  access immediately without canceling unresolved work.
- Charged academic terms keep their year/semester/calendar identity. Opening or
  closing them preserves charges; closing still allows later audited reversals.
  No charge, payment, receipt or university acknowledgment is created by term setup.

Normal new active-slot and encounter saves query current provider/account
eligibility rather than trusting cached related objects. Booking locks provider
account, provider, room and slot in a consistent resource order before validating;
it avoids PostgreSQL FOR UPDATE on a nullable outer join. Later slot/clinical
services must preserve that lock order and recheck eligibility. These are
application guards, not new database constraints or proof of PostgreSQL concurrency.

## Step 5 patient details and intake

- Patient self-service resolves the Patient by the signed-in account. Emergency
  contact IDs are scoped to that Patient for editing and removal. Primary
  replacement is atomic and retains the previous contact as a secondary contact.
  The database allows zero or one primary contact.
- Admin's patient directory at `/clinic/patients/` shows operational identity and
  affiliation fields. New or attached profiles require explicit affiliation
  confirmation. A legacy affiliation stays unknown until reviewed. Corrections
  apply to the current Patient and User, preserving account roles, profile links
  and visit affiliation snapshots. Admin intake does not expose allergy or visit notes.
- Allergy review requires an active, qualified Provider and a current care
  relationship, including a Nurse's access to today's Draft triage queue.
  The clinician workflow denies self-editing. The patient sees the recorded list
  through their own details page. Allergy changes record the actor and row ID in
  the audit log and preserve the original recording timestamp. Empty lists
  indicate that allergies are undocumented. No allergy deletion is exposed.

## Step 6 availability

- Active Admins can see every slot and schedule any eligible provider. An Active
  Provider with a reviewed clinical designation can see and manage only their
  own slots. These pages expose slot and resource details without patient identity
  or appointment notes.
- Future slots can use any active clinic room. Open slots cannot overlap another
  active slot for the same provider or room. Manila dates drive filtering and
  display. A resource must be active to open, reopen or change a schedule.
- A slot that has started, has a non-canceled appointment, or has a visit linked
  through an appointment is read-only. Canceled-only history fixes the provider,
  room, and times. Eligible future slots with only canceled appointments may
  still open or close. An Admin can close an unbooked future slot after its
  provider becomes ineligible.
- Slot writes lock old and requested resources in booking order and record an
  audit event in the same transaction. Stale form submissions are rejected.
  PostgreSQL range exclusions guard active overlaps at the database boundary.

## Step 7 booking and cancellation

- The appointment pages resolve the Patient from the signed-in account. An
  Admin or Provider can use the same pages for their own Patient profile.
  The appointment reason and history are visible only to the owner on these pages.
- Browse results include only future, open slots with an eligible provider,
  active room and no protected appointment. Booking rechecks slot version,
  eligibility and conflicts inside the transaction. The pages show Manila time.
- The owner can cancel or reschedule a future Scheduled appointment before its
  start when it has no linked visit. The existing Admin service can cancel on
  behalf of another patient under the same state rules. It records a distinct
  audit event. The appointment pages use own-account scope for every role.
- Rescheduling saves the original cancellation and replacement together. A failed
  replacement preserves the original appointment and its audit history.
  Booking and cancellation lock the Patient, then the involved accounts,
  providers, rooms and slots in primary-key order. An existing Appointment is
  locked after its slot.

## Step 8 reception and encounter intake

- Admin can manage the operational queue and start a walk-in by exact active
  patient ID. A qualified Physician or Dentist accesses their own scheduled
  appointments and assigned encounters. Nurses also see today's appointments
  and Draft triage encounters. The queue displays scheduling, identity and
  assignment details without clinical notes or appointment reasons.
- A Scheduled appointment can be checked in during its Manila clinic day
  before the slot ends, or marked No show after its end if no encounter is
  linked. Admin may cancel under the existing future Scheduled rules. A
  Checked in appointment requires a finalized linked encounter to move to
  Completed. Terminal statuses stay closed.
- One Draft can open for a Checked in appointment. A walk-in has no appointment.
  Intake uses the patient's known affiliation and the server timestamp. Admin
  and the Nurse within their triage scope can change the attending provider of
  a Draft; the scheduled provider stays on the slot. Active designation and
  ownership checks are repeated in the write transaction.

## Step 9 consultation and vitals

- The clinical worklist requires an eligible active practitioner. Physicians
  and Dentists see their assigned Draft and Finalized visits. Nurses see their
  assigned Drafts and the current Manila day's Draft triage encounters. Clinical
  pages exclude the practitioner's own patient encounter. A nonclinical Admin
  uses reception without access to the clinical workspace.
- Nurses see allergy alerts and current encounter vitals. The assigned
  Physician or Dentist can also review the notes, diagnoses and recent
  finalized visits within the existing care relationship. The clinical pages
  contain no patient-facing summary.
- Only the attending Physician or Dentist edits or finalizes the Draft.
  Every clinical write rechecks permissions and version after taking the same
  patient, account, resource and encounter locks used by reception. The server
  assigns the vital-sign author and timestamps. Audit entries omit note content.
- Finalization requires saved complaint, symptoms or examination notes, and a
  treatment plan. Vitals and diagnosis are optional. A linked Checked in
  appointment becomes Completed atomically. Finalized notes and details are
  read-only. Patient summaries and controlled amendments remain separate work.
- Admin adds catalog entries from reviewed sources or clearly fictional
  examples. Practitioners can select several distinct diagnoses and at most one
  primary diagnosis. Linked catalog entries cannot be rewritten.

## Step 10 prescriptions

- Clinic Admin manages catalog entries. Linked medication codes, names,
  strengths and dosage forms remain stable. Deactivation removes a formulation
  from new selection and prevents issue if it remains on a draft.
- An eligible attending Physician or Dentist can start one open prescription
  draft per Draft encounter. A prescription author edits their own draft and
  confirms issue after saving at least one valid item. Server time and the
  prescriber account determine issuance. Finalization requires all drafts on
  the encounter to be issued or discarded first.
- The current eligible attending can discard a draft after reassignment or
  cancel an issued prescription, leaving the original prescriber, items and
  issue timestamp intact. Replacement starts a separate audited draft for the
  same patient on an assigned Draft encounter. A finalized encounter requires
  a new intake before that replacement can be issued.
- The signed-in patient sees only their own issued and subsequently canceled
  prescriptions. Discarded drafts remain private. Print copies visibly mark
  canceled status and prototype use. The workflow does not track stock or
  dispensing.

## Step 11 referrals and patient visit summaries

- The assigned active Physician or Dentist can create a Pending referral on
  a Draft encounter. Destination and reason are patient-facing. The server
  sets the original author and timestamp and records the action in audit.
- The current assigned eligible clinician can mark a Pending referral
  Completed or Canceled on a Draft or Finalized encounter. The recorded
  status describes clinic follow-up. Original content, author and time
  are immutable from creation, and terminal statuses cannot be reopened.
  Correct a referral on a Draft by canceling it and recording a new one.
- A signed-in patient sees only their own Finalized visits. The projection
  includes the date, type, attending provider, chief complaint, catalog
  diagnosis labels, current issued prescriptions and referral information.
  It excludes symptoms, examination and treatment notes, diagnosis link
  notes, vitals and appointment reasons. Canceled prescriptions stay in
  separate prescription history.
- Patient summary and referral print pages use the same ownership check
  and are read-only. They are prototype copies and any external appointment
  remains a separate arrangement.

## Step 12 student tuition charges

- Clinic Admins can find encounters by exact University ID and create positive
  PHP charge lines for visits with a Student affiliation snapshot. Faculty and
  Staff visits have no charge form or zero-value line. New lines use generic
  prototype descriptions. Billing pages show the encounter number and status
  without opening the clinical record.
- Admins can export Pending lines as CSV with an optional term filter. The file
  includes the charge code, University ID, term, description, amount and currency.
  The export reads charge data without posting anything.
- New charges require an open term. Posting also requires a Finalized visit and
  explicit confirmation. Pending voids and simulated reversals require an
  administrative reason and confirmation. A closed term still allows reversal.
  Retries of the same submission preserve the charge and its audit history.
- Accounts with a Patient profile can read their own charge lines and status,
  including Admin and Provider accounts with a secondary profile. Internal
  reversal reasons and billing references stay in the Admin billing detail page.
- The prototype generates `DEMO-POST-` and `DEMO-REV-` references. These track
  the simulation inside TeknoCare. No university finance service receives them.

## Step 13 audit history and operational reports

- Active Clinic Admins can browse the append-only audit history. Filters
  include actor University ID, action text, target table, target ID and a
  Manila date range. The viewer displays audit metadata without opening the
  target record.
- Authorized opens of the clinical workspace record the actor, timestamp,
  action and encounter ID. Note views and vitals-only views have distinct
  actions. Audit entries never copy notes, vital readings or credentials.
- Reports display appointment, visit, provider workload, affiliation,
  referral and tuition charge aggregates. Dates use scheduled slot start,
  visit time, referral time and charge creation time respectively. Statuses
  come from current source rows. Historical affiliation comes from the visit
  snapshot. Tuition totals group by term and currency with a separate amount
  for each status.
- Reports exclude records linked to the four exact retired JOIN-demo
  identities. Existing assessment rows remain in the database. The Step 12
  Pending-charge CSV stays available through the Admin billing workflow.

## Limits before any real deployment

This prototype lacks login/reset throttling, MFA, verified enrollment/personnel
identity, email recovery and production recovery operations. Keep demonstrations
local and fictional; do not expose it publicly or use real health information.
Database-owner/raw SQL access can bypass application permission checks. PostgreSQL
grants, Supabase exposure/RLS and representative migration/concurrency behavior
require the separate staging/backup checkpoint. SQLite tests are not evidence of
hosted deployment or production security certification.
