# TeknoCare prototype development plan

Prepared November 18, 2026, from repository revision `866f313`.

## Goal and working agreement

Build a functional CIT-University clinic school-project prototype: a patient can
register, maintain contact information, book care, attend a scheduled or walk-in
visit, and view released visit information. Clinic personnel can manage schedules,
document care, issue demonstration prescriptions/referrals, and record student
tuition charges. Faculty and Staff care is free under the project's agreed rules.
These rules are project requirements, not independently verified university policy.

Implement one approved step at a time. This document is a plan, not authorization
to implement all steps now. After each step, provide the changed files, behavior,
checks and results, remaining limits, manual visual checks and expected outcomes,
exact Git commands, and a suggested commit message. The student reviews, commits,
and pushes. Do not commit, push, or advance into another feature automatically.
If a step needs smaller commits, give each delivered change its own commands and
message. Update this plan's progress and decision records with the implementation.

User preference, November 18, 2026: do not use Computer Use or browser UI automation,
and do not capture/request screenshots. The user personally checks visual layouts
and behavior, then confirms in chat. Supply concise page/action/expected-result
checklists and record visual review as pending until the user confirms. CLI and
HTTP verification remain part of the agent's work. This supersedes earlier capture
requirements in historical handoffs and assessment documents.

## Review baseline

Reviewed first-party application Python, models, services, forms, routes, templates,
CSS/JavaScript, tests, migrations, verification scripts, ERD schema generator and
rendering utilities, project configuration, and SQL activity implementation/docs.
The installed virtual environment and generated diagram files are dependencies
and outputs, rather than application source to rewrite. No `.env` values, live
patient records, or hosted database contents were needed for this review.

ERD authority is the checked-in [ERD guide](erd/README.md),
[schema source](erd/generate_erd.py), [data dictionary](erd/data_dictionary.md), and
[implementation notes](erd/model_implementation.md). They describe 22 entities and
28 foreign keys. The original `BENITEZ_physicalERD.pdf` is referenced in the docs
but is not present in the repository reviewed here. Any requirement unique to that
original attachment must be reconciled if it is supplied later.

| Area | Exists now | Work still needed |
| --- | --- | --- |
| Identity | Custom `register.User`, hashed passwords, sessions, basic login/logout | Password validation in registration, password change/recovery, identity normalization, complete role/profile provisioning, suspension tests, protected actions |
| Registration | Transactional Student account, Patient, primary emergency contact creation | Honest membership-verification boundary; personnel onboarding; duplicate races and stronger validation |
| Profile/settings | Own phone/address/bio editing; saved preference checkboxes | Patient demographics/contact management; theme behavior; explain inactive notification delivery |
| Dashboard | Greeting and profile/settings links | Role-specific tasks and actual clinic data |
| Patients/providers/university | Models for patients, contacts, allergies, practitioners, departments | Forms, services, pages, permissions, lookup administration |
| Scheduling | Room/Slot/Appointment models, booking/cancellation services, overlap/uniqueness guards | Availability and booking screens, actor/ownership checks, full transition rules and concurrency verification |
| Clinical | Walk-in/scheduled MedicalRecord, vitals, diagnoses, referrals | Triage/consultation UI, clinical authorization, finalization and child-record history protections |
| Prescriptions | Medication, Prescription, PrescriptionItem with normal-save validation | Authorized issuing/cancellation workflow, printable output, protection against bulk/history bypass |
| Billing | Terms, student charges, posting/void services, database guards, some audits | Staff screens, demo acknowledgment/export/reconciliation, student view |
| Audit | Append-only model and database guards | Coverage across features and restricted review UI |
| Django admin | Route and custom-user compatibility helpers; Profile/Settings registered | Safe account provisioning; clinical/billing changes must use protected workflows |
| SQL learning activity | Removed in Step 0; assessment documents archived under `docs/archive/sql_joins/` | Existing fictional rows retained; any later data cleanup is a separate reviewed action |
| Configuration | Environment database URL and secret, pinned requirements | Separate local/staging configuration, Manila presentation time, deploy/static setup and documented startup |

Specific gaps to address in their owning steps:

- `RegistrationForm` compares passwords but does not call Django password validators.
  Its Student affiliation is assigned automatically; there is no university lookup.
- `school_id` is a unique string of at most 20 characters. Student-looking IDs in
  tests are examples, not evidence of CIT-U's personnel or student ID format.
- `User.is_staff` and `is_superuser` currently treat every Admin as fully privileged.
  This custom User has no Groups/PermissionsMixin system to assume is available.
- Booking/cancellation services lack an actor argument and complete state/ownership
  rules. Booking must recheck provider/room eligibility when availability is used.
- A finalized parent record is protected, but that alone does not freeze its vitals,
  diagnosis links, referrals, or prescriptions. Their workflows need explicit rules.
- The dashboard promises name/age editing although the profile form only edits
  phone/address/bio; profile JavaScript targets a removed name field.
- Dark mode and email notification preferences are saved but do not currently
  implement a theme switch or notification delivery. Registration success messages
  are not displayed by the login template. Navigation uses a GET sign-out link.
- Historical SQL activity docs describe some retired model locations and relations;
  treat them as assessment history, not the current ERD specification.
- Configuration currently uses `DEBUG = True`, empty `ALLOWED_HOSTS`, and UTC
  presentation time. Hosted migration status cannot be inferred from source files.

Baseline validation on November 18, 2026: 57 tests discovered; 56 passed and one
PostgreSQL-only exclusion test was skipped on isolated in-memory SQLite. Django
system checks reported no issues, and `makemigrations --check --dry-run` detected
no changes. ERD metadata matched all 22 entities/28 relationships; the populated
legacy SQLite upgrade verification passed. These results do not verify hosted
deployment, PostgreSQL concurrency, or the visual behavior of running screens.

## Prototype scope and unresolved policy

Use fictional data throughout development, demonstrations, manual reviews, and exports.
The app demonstrates workflows; it is not an approved clinical, identity, or
university finance system. Keep Django server-rendered feature slices and the
existing blue-green/teal visual style. No SPA, public API, or background worker is
needed for the selected scope.

| Decision | Proposed prototype default | Boundary / revisit point |
| --- | --- | --- |
| University IDs | Store as text, trim whitespace, preserve leading zeros; reject blank/duplicate IDs | Confirm student, faculty, staff, and contracted practitioner examples before a restrictive regex or case policy. Audit existing values before normalization/uniqueness migrations. |
| Membership | Public registration is explicitly for demonstration Student accounts; Admin creates Faculty/Staff and practitioner accounts | No SIS/HR verification or SSO. Do not describe a submitted ID or email as verified membership. If approval/verification tracking is required, design the field/workflow explicitly before implementation. |
| University email | Validate email syntax and agreed uniqueness normalization | Do not invent a required CIT-U email domain or exclude personnel using another approved address. |
| Provider identity | Existing User fields plus provider type, optional license, specialization, activity status; optional contact profile | No payroll, HR records, credential images, or external license lookup. Fictional credentials must be labeled fictional. Decide how contracted providers without university IDs log in before provisioning them. |
| Provider permission | Explicit application policies for active verified-designation practitioners; Physician/Dentist demonstration prescribing, Nurse triage/vitals | This is a prototype permission rule, not a claim about professional or university prescribing policy. Admin status and provider FK existence alone never grant clinical authority. |
| Accounts receiving care | Admin and Provider may also have a Patient profile using their existing login | Primary account role and Student/Faculty/Staff affiliation remain separate. No duplicate account is needed to receive care. |
| Patient record access | Own finalized visit summary, issued prescriptions, referrals, appointments and charges | Draft/internal notes are staff-only. Define the released summary fields; the current ERD has no separate release-status field. |
| Provider record access | Assigned visits and relevant history for patients under their care; Nurse triage limited to operationally relevant visits | No unrestricted patient directory/full-history access by URL guessing. Deny self-finalization/self-prescribing in the prototype. Agree staff handoff rules in Step 2. |
| Administrative access | Accounts, membership details, schedules, reference data, charges and audit metadata | Nonclinical Admin cannot author/finalize notes or prescribe. Restrict sensitive clinical content and protect Django admin bypass routes. |
| Payments | No payment collection. Student charge lines represent additions to tuition; personnel visits have no charge rows | No Pay Now button, cards/e-wallets, receipts, tuition balances, scholarships, insurance, or paid/unpaid settlement. Posted never means paid. |
| Finance integration | In fictional demo data, simulate manual acknowledgment/reversal using conspicuous `DEMO-` references and a prototype notice | No university finance connection exists. Exports leave charges Pending; real Posted status would require actual verified university acknowledgment. Do not simulate success in a database containing real records. |
| Fees | Admin enters positive line amounts/descriptions in PHP; free services create no charge | No invented official fee schedule or automatic medication pricing. Historical charge amounts remain fixed. |
| Clinic operations | One clinic workflow using explicit provider/room/time slots; scheduled care and walk-ins | No inferred campus hours, holidays, priority scoring, or automatic triage advice. Use configurable fictional schedules until supplied. |
| Appointments | Immediate booking of available slots; cancel/rebook for rescheduling; server-enforced state changes | One live booking per slot. No approval queue, waitlist, recurrence engine, or automatic no-show penalties. |
| Corrections | Edit drafts; finalization/issuance locks historical content; cancel/replace issued prescriptions | A clinical addendum/amendment entity is absent. Full amendment support is deferred unless approved with an ERD update; an audit event is not a substitute for storing clinical addenda. |
| Allergies | Record known patient allergy rows; show no rows as "Not documented" | The schema does not distinguish confirmed no allergies from unknown. Add explicit status only if requested and reflected in the ERD. |
| Referrals | Record destination/reason and manual Pending/Completed/Canceled follow-up | No outside hospital API, appointment booking, attachments, or separate completion timestamp in the current schema. |
| Notifications | On-screen feedback and dashboard reminders; real theme preference | Email/SMS/push delivery and scheduled reminder jobs deferred. Hide/disable or clearly label the saved email setting as inactive. |
| Documents | Browser-printable prototype prescription/referral/visit summary where useful | No official medical certificates, clinician signatures, uploaded scans, document-verification service, or legal validity claim. |
| Academic calendar | Admin-maintained terms and dates with open/closed charge flag | Do not invent official semesters, enrollment checks, or automatic billing-term assignment. |

Other exclusions: inventory/dispensing, medicine stock, laboratory requests/results,
immunization tracking, support tickets, university enrollment/payment integration,
telemedicine, file uploads, and automated clinical advice. A medication catalog
does not establish that medicine was dispensed.

Before the relevant step, record any newly supplied campus policy, example IDs,
working hours, fee list, or instructor requirement here. Unknown university facts
do not block building a fictional prototype with documented defaults. Schema
expansion requires a concrete proposal and an ERD/model/migration update together.

## ERD rules to preserve

1. Keep `AUTH_USER_MODEL = 'register.User'`, existing primary keys and physical
   table names; names belong to User, birth date to Patient, contacts to their own
   rows. Required Patient/Provider subtypes are provisioned atomically.
2. Patient affiliation and account role are independent. Unknown legacy affiliation
   remains unknown. Never infer birth dates, licenses, diagnoses, or medicine doses.
3. A Slot owns provider, room, start/end; Appointment obtains provider through Slot.
   Preserve canceled bookings; derive booking state and no-show counts.
4. One appointment can link to at most one encounter. Walk-ins have no artificial
   appointment. Actual attending provider may differ from scheduled provider.
5. Opening a visit snapshots affiliation server-side. Personnel encounters cannot
   generate StudentCharge rows. Later affiliation changes do not rewrite history.
6. Preserve diagnosis/system uniqueness and one primary diagnosis per record;
   allow multiple observations, medicines, charges, and referrals as modeled.
7. Finalized/issued/posted history is protected. Deactivate/cancel/void rather than
   deleting referenced clinical or financial data. Audit writes occur with writes
   they describe, and do not copy passwords or full clinical notes.
8. Use timezone-aware timestamps and Asia/Manila presentation for the clinic.
   Currency amounts use Decimal. An export is neither posting nor payment.
9. Preserve original migrations, `legacy_*` archives and `BASELINE_COMMIT.txt`.
   No destructive reset, fake migration, or hosted upgrade to bypass a mismatch.
10. PostgreSQL range exclusions/locking/triggers require disposable PostgreSQL
    verification. SQLite passing does not establish concurrent PostgreSQL behavior.

## Ordered implementation steps

All steps start Pending. Dependencies below are implementation dependencies, not
requests to deliver multiple steps in one turn. Each should produce one reviewable
feature checkpoint; split a large step into named substeps before implementing it.
Audit events and negative authorization tests accompany each write feature from
Step 2 onward; they are not postponed until the audit viewer is built.

### Page and feature deliverables

The steps include creating and changing the actual working pages, not only models
or backend code. Each feature includes its Django routes, forms, views, templates,
CSS/JavaScript where needed, services, permissions, validation and appropriate tests.
Existing login, registration, dashboard, navigation, profile and settings pages
will be updated. New pages cover reference-data administration, personnel intake,
patient details, availability, appointments, today's queue, consultations, vitals,
diagnoses, prescriptions, referrals, visit summaries, charges, audits and reports.
List/detail/create/edit/print pages are added where the workflow needs them; final
page boundaries can be refined during each step. Every changed running interface
requires the user's manual visual review and confirmation, without screenshots.

### Step 0 — Remove the completed SQL JOIN school demonstration

Depends on: review of this plan. Requested November 18, 2026, because the school
demonstration is complete. This is application cleanup before new clinic work.

Implementation: removed November 18, 2026, after the student requested Step 0.
The runtime app, route, navigation entry, stylesheet, templates, demo commands and
demo-only tests are deleted. Historical assessment docs are clearly marked under
`docs/archive/sql_joins/`. Clinic schema/migration source, existing rows, legacy
archives and baseline evidence are unchanged. See the
[Step 0 confirmation and Git handoff](step_0_verification.md) for current results
and any outstanding visual review. Supabase was not connected to or modified.

- Remove the SQL joins navigation entry, `/joins/` route and `apps.joins` installed
  app. Remove its views, queries, fictional seed/verification commands, templates,
  stylesheet and demo-only tests, after checking all references.
- Remove active setup/video instructions for the retired demonstration. Move any
  assessment evidence worth retaining into a clearly marked historical docs folder;
  Git history also preserves the previous implementation. Update `AGENTS.md` and
  active documentation so they no longer instruct developers to maintain the demo.
- Preserve the real User, Patient, Provider, Slot and Appointment models/tables,
  ERD, migrations, clinic tests, `BASELINE_COMMIT.txt` and `legacy_*` archives. The
  joins app owns no clinic tables, so removing it does not require dropping them.
- Do not create the old JOIN-DEMO seed data in new prototype databases. Existing
  fictional rows are a separate data-cleanup decision: first identify exact
  reserved ID/email matches and dependencies, then report the proposed rows.
  Do not delete by name or prefix alone, and do not remove hosted rows merely
  because the demonstration code was retired. Retain ambiguous/reused records;
  exclude remaining known demonstration fixtures from operational reports.

Acceptance: clinic/account pages work without `apps.joins`; no navigation or active
setup instructions reference the removed feature; `/joins/` is unavailable; checks
and the remaining test suite pass. Removing source code leaves existing clinic
database records intact. The user checks the changed navigation/dashboard and
confirms the expected results in chat; no screenshots are required.

Commit: `chore: remove completed SQL join demonstration`

### Step 1 — Reproducible local setup and baseline

Depends on: review of this plan. The student explicitly requested Step 1 before
Step 0 on November 18, 2026; setup can proceed independently. SQL demo removal
was subsequently completed in Step 0 as a separate checkpoint.

Implementation: prepared November 18, 2026; awaiting student verification/approval.
See [startup and confirmation steps](../README.md) and the
[Step 1 evidence/Git handoff](step_1_verification.md). Local/test settings, demo
bootstrap, automated checks, GitHub CI and the Supabase runbook are implemented.
Django is upgraded to 5.2.19 LTS, with a retained-original profile replacement
migration and POST sign-out compatibility. No hosted database was inspected or
migrated. PostgreSQL CI/staging and user-confirmed visual review remain pending.

- Add startup/development instructions, a credential-free `.env.example`, and an
  isolated local/test settings path. Keep the configured hosted database separate.
- Make debug/hosts explicit configuration; set local clinic display time to
  Asia/Manila; document static-file and deployment requirements.
- Verify custom User compatibility and current dependency support from official
  documentation before any version change. Plan a small compatibility update if
  needed; preserve the custom identity model.
- Provide a repeatable local fictional demo setup with an Admin login; generate or
  accept demo credentials explicitly without committing secrets. Do not reuse or
  recreate the retired JOIN-DEMO assessment accounts.
- Rehearse current migrations locally; report schema gaps without touching hosted
  data. Introduce a small automated check workflow if repository hosting supports it.
- Prepare the Supabase migration inventory and staging/backup procedure described
  below. Keep app preview on a migrated isolated database until the configured
  Supabase schema has passed its own migration checkpoint.

Acceptance: a fresh checkout can install, configure, migrate an isolated database,
create the demo Admin, run checks, and start the app using documented commands.
ERD metadata and populated legacy upgrade checks pass. PostgreSQL verification is
a separate explicit gate if a disposable instance is not available.

Commit: `chore: establish reproducible prototype development setup`

### Step 2 — Authentication, provisioning and authorization foundation

Depends on: 1.

Implementation: prepared November 18, 2026 after the student pushed Step 0.
See the [access matrix and prototype limits](access_policy.md) and
[verification/Git handoff](step_2_verification.md). Account services, server-side
policies, password pages, safe login redirects, required-profile/session checks
and read-only Django admin are implemented. Existing appointment/billing services
now enforce actor authorization. The normalized-identity index migration preserves
ERD columns and refuses legacy collisions without rewriting data. User visual
approval and PostgreSQL/hosted rehearsal remain pending; no Supabase migration
has been applied. Later reference, appointment and clinical screens remain planned.

- Add shared, small role/object policy helpers; enforce at the server and service
  boundary. Define patient ownership, assigned clinical access, nursing triage,
  clinical finalization/prescribing, and Admin operations explicitly.
- Call password validators, handle duplicate-registration races, normalize agreed
  identity fields, and test suspended users and existing-session behavior.
- Create role/subtype provisioning services; reject missing required profiles
  cleanly rather than crashing. Keep Admin/Provider patient-profile coexistence.
- Use POST+CSRF logout and other mutations; handle safe return-to-page redirects.
  Add password change and a documented Admin-assisted reset for fictional accounts.
  No email recovery claim without a configured delivery mechanism.
- POST sign-out was brought forward into Step 1 for Django 5.2 compatibility;
  retain it while extending the remaining account security workflows here.
- Keep a bootstrap Admin path available without granting ordinary clinic Admin
  unrestricted model editing through Django admin. Verify custom-user forms before
  registering User with the admin site.

Acceptance: anonymous, suspended, wrong-role and wrong-owner requests fail; crafted
POSTs cannot set role, affiliation, patient, creator or prescriber. Password change
invalidates old sessions. The complete role/action matrix has meaningful tests.

Commit: `feat: enforce account provisioning and clinic access policies`

### Step 3 — Shared interface and role dashboards

Depends on: 2.

Implementation: prepared November 18, 2026 after the Step 2 commit. All clinic
pages now extend a shared base with accessible form/error/status patterns,
responsive light/dark styles and saved account-specific theme. Role dashboards
show only working tasks and own-account context; profile and email-delivery copy
is corrected. Reusable table/empty/pagination patterns support later list pages.
See [interface conventions](interface_patterns.md) and the
[manual verification/Git handoff](step_3_verification.md). No new schema or hosted
database change is needed. The user confirmed their checks looked good before
requesting Step 4; Step 3 manual review is approved.

- Introduce a base template, shared navigation, messages/errors, form/table styles,
  pagination patterns, accessible focus/labels, and mobile layouts.
- Show Patient, Provider and Admin tasks appropriate to permissions. Add data cards
  only when their backing feature exists; avoid links to unfinished screens.
- Correct stale profile copy/focus targets, wire dark mode to the stored preference,
  and clearly label unavailable email delivery.
- Keep the retired SQL demonstration absent from navigation and clinic workflows;
  its application removal is completed in Step 0.

Acceptance: every role has a useful home and working navigation; saved theme applies
across pages; success/error messages display; forms and navigation work on mobile.

Commit: `feat: add shared clinic interface and role dashboards`

### Step 4 — University, provider, room and term administration

Depends on: 3.

Implementation: prepared November 18, 2026 after Step 3 manual approval and commit
`826a606`. Admin-only Clinic setup pages now manage departments, rooms, academic
terms, provider provisioning/attachment/review, Faculty/Staff accounts and
non-Admin account access. Service authorization, atomic audit, protected references
and conservative deactivation rules preserve history. Optional unknown licenses
stay NULL, and activation requires explicit prototype manual review. Scheduling
and encounter eligibility now checks fresh account/provider state. No new schema
or hosted migration is required. See [the Step 4 checks and decisions](step_4_verification.md).
Isolated tests and HTTP checks pass; Step 4 user visual review and PostgreSQL
staging/concurrency verification remain pending. Patient intake/allergies and
actual availability/clinical workflows stay in their planned later steps.

- Build restricted lists/forms for Department, ClinicRoom, AcademicTerm and Provider.
  Provision Faculty/Staff/Provider accounts through the Step 2 services.
- Use actual supplied or clearly fictional lookup values; verify provider
  designation and activation separately from account activity. Normalize blank
  optional licenses to NULL; do not fabricate professional credentials.
- Protect referenced rows; prefer deactivate/close. Ensure an Admin who is also a
  Provider gains clinical powers only through the clinical policy.

Acceptance: Admin can prepare a room, practitioner and open term; other roles cannot
change them. Inactive/unverified practitioners cannot schedule or treat patients.
Deactivation preserves historical visits and charges.

Commit: `feat: manage clinic reference data and practitioner accounts`

### Step 5 — Patient profile, personnel intake and allergies

Depends on: 4.

- Patient edits permitted personal contacts, date of birth and emergency contacts;
  account identity/affiliation corrections use authorized staff workflows.
- Add Admin patient search/intake for Student/Faculty/Staff with minimum necessary
  details; support an existing Provider/Admin receiving care under the same login.
- Add structured allergy entry/review with clear authorship limits; patients may
  view the recorded list, with clinical edits restricted to authorized staff.
- Preserve at most one primary contact, future-birth-date validation and unverified
  legacy exceptions. Do not ask patients to invent a medical history to register.

Acceptance: ownership isolation, patient subtype coexistence, primary-contact
updates, age derivation and personnel intake work; a patient cannot change their
own billable eligibility or read another patient's details.

Commit: `feat: add patient intake contacts and allergy management`

### Step 6 — Provider and room availability

Depends on: 4 and 5.

- Admin manages slots; active Providers manage their own future availability under
  agreed room rules. Start with explicit individual slots and date filters.
- Enforce active accounts/provider/room, future times, duration and provider/room
  overlap. Define deactivation behavior for already booked slots.
- Restrict edits when booked or linked to clinical history; preserve original
  appointments rather than silently moving people to another room/provider/time.

Acceptance: authorized users create valid nonoverlapping availability in Manila
time; inactive resources and occupied/history-linked edits are rejected. Exercise
database exclusions on disposable PostgreSQL before calling concurrency verified.

Commit: `feat: manage provider and room availability`

### Step 7 — Patient appointments and cancellation

Depends on: 5 and 6.

- Browse future available slots, filter by date/provider/type, book with a reason,
  show confirmation and own upcoming/past appointments.
- Extend services with actor/ownership checks and fresh resource validation. Handle
  stale slots/concurrent booking as understandable form errors.
- Patient cancels only their eligible Scheduled booking before its start;
  Admin exceptions are explicit and audited. Rescheduling cancels and rebooks;
  keep the old booking if a transactional replacement fails.

Acceptance: no double slot booking or overlapping live patient booking; cancellation
retains history and frees only an eligible future slot; cross-patient requests and
repeated terminal-state actions fail safely.

Commit: `feat: add patient booking cancellation and appointment history`

### Step 8 — Reception, check-in and walk-in encounters

Depends on: 7.

- Add today's operational queue for Admin and authorized practitioners. It is a
  filtered view of appointments/visits, not a new queue-management entity.
- Implement Scheduled -> Checked-In, Scheduled -> No Show after the slot ends,
  eligible cancellation, and Checked-In -> Completed only with finalized care.
  Define any permitted exception explicitly; terminal states cannot be reopened.
- Open one Draft encounter for an attended booking, or a walk-in without a slot;
  capture verified-for-demo affiliation from Patient, not request data.
- Assign/reassign draft attending provider with permission/audit checks; distinguish
  scheduled practitioner from actual attending practitioner.

Acceptance: duplicate requests cannot create duplicate appointment encounters;
canceled/no-show appointments cannot open care; walk-ins do not consume invented
availability; identity/affiliation consistency holds.

Commit: `feat: add check-in walk-in intake and encounter assignment`

### Step 9 — Vitals, consultation, diagnoses and finalization

Depends on: 8.

- Nurses/authorized practitioners record timestamped vitals on permitted Draft
  visits; record the actor server-side. Show allergy alerts and relevant history.
- Attending authorized clinician edits complaint, symptoms, examination, treatment
  and multiple catalog diagnoses; support at most one primary diagnosis.
- Add explicit finalization with agreed required fields (at least complaint,
  consultation/treatment documentation and accountable clinician). Never force an
  invented diagnosis or a vital measurement that was not taken.
- Lock clinical child edits as well as parent notes after finalization. Distinguish
  later referral follow-up from rewriting finalized referral content. Refuse stale
  edits that would overwrite newer work; lock/recheck state transactionally.
- Complete linked Checked-In appointment atomically with finalization. Keep Draft
  editing separate from a future, currently deferred, addendum design.

Acceptance: Nurse and nonclinical Admin cannot finalize; another provider cannot
edit an unassigned case; finalized notes/vitals/diagnosis history resist ordinary
and exposed bulk/admin bypass. Invalid vitals and duplicate/primary diagnoses fail.

Commit: `feat: document consultations and protect finalized clinical history`

### Step 10 — Medication catalog and prescriptions

Depends on: 9.

- Add protected medication catalog administration and prescription draft/items
  editing for authorized prescribers on their encounters.
- Issue only with at least one valid item and authorized active prescriber; use
  server timestamp/actor and preserve dose, route, frequency, duration and quantity.
- For a simple lifecycle, issue during the Draft consultation before finalization;
  finalization rejects unresolved prescription drafts. Issued content remains locked
  even while the consultation is Draft. Later corrections cancel/replace through
  an explicit audited workflow preserving the finalized encounter.
- Prevent bulk/admin edits to issued items and referenced formulations. Provide a
  clearly marked prototype print view, without suggesting stock or dispensing.

Acceptance: unauthorized issuing, empty prescriptions and invalid quantities fail;
issued/canceled history and catalog formulation are preserved under concurrent
actions; patient sees only their issued/canceled history, never another person's.

Commit: `feat: add authorized prescription drafting issuing and printing`

### Step 11 — Referrals and patient visit summaries

Depends on: 10.

- Add clinician-created referrals with destination/reason on the Draft encounter;
  preserve their clinical content after finalization.
- Permit audited follow-up Pending -> Completed/Canceled without rewriting the
  original referral; no external appointment or treatment is inferred.
- Publish a defined summary of Finalized encounters to the owning patient with
  issued prescriptions and referral instructions; exclude Draft/internal content.
- Add useful prototype print pages without claiming an official medical certificate.

Acceptance: patients cannot view drafts or change referral status; follow-up keeps
original referral content; scheduled and walk-in summaries work with optional data.

Commit: `feat: add referrals and patient visit summaries`

### Step 12 — Student tuition charge prototype

Depends on: 4, 9 and 11.

- Add Admin charge creation/list/detail filtered by term/status; use existing
  create/post/void services and strengthen actor/transition validation as needed.
- Offer positive PHP lines for historically Student encounters; show personnel care
  as free without inserting zero-value rows. Patients only read their own charges.
- Export Pending lines with stable charge code, student ID, term, description,
  amount and currency; omit clinical notes/diagnoses and protect CSV cell handling.
- Exports keep Pending status. In the fictional prototype, an explicit simulated
  acknowledgment records a `DEMO-` reference and unmistakable simulation notice.
  No production finance endpoint or claimed university acknowledgment is present.
- Demonstrate Pending -> Posted/Voided and Posted -> Voided only with simulated
  reversal confirmation; keep immutable original lines and retry idempotency.

Acceptance: Faculty/Staff charges fail even through database bypass; Draft visits
cannot post; closed terms block new charges/postings but allow reversal; retries do
not duplicate lines; export does not post or pay; no screen calls Posted "Paid".

Commit: `feat: add simulated tuition charge posting and reconciliation`

### Step 13 — Audit viewer and operational reports

Depends on: 12.

- Add restricted append-only audit browsing by actor/action/target/time; audit
  feature writes already exist from earlier steps. Include high-value record reads
  where useful without logging full clinical content or secrets.
- Add simple date-filtered appointment/visit counts, no-shows, provider workload,
  Student versus personnel visits, referral status and charge totals by term/status.
- Exclude JOIN-DEMO fixtures from clinic operational reports, paginate lists, and
  reconcile totals against source rows. Separate Pending/Posted/Voided sums.
- Keep financial exports restricted and clinical reporting appropriately scoped;
  aggregate counts are sufficient for a school demonstration.

Acceptance: report filters/totals agree with fictional source cases; protected
records cannot be modified via the viewer; patient/Provider access cannot reveal
unrelated clinic or billing data.

Commit: `feat: add clinic audit review and operational reports`

### Step 14 — Integrated testing, PostgreSQL rehearsal and demonstration handoff

Depends on: 13.

- Run full role/ownership/state transition tests and end-to-end Student, Faculty,
  Staff, Nurse, Physician/Dentist and Admin-as-patient scenarios.
- Verify simultaneous booking, provider/room exclusions, patient overlap, duplicate
  finalization/issuing/posting and trigger behavior on disposable PostgreSQL.
  Correct failures in the relevant feature and document any remaining limitation.
- Rehearse populated legacy upgrade, backup/restore and unverified-data review on
  staging before any separately authorized hosted database migration.
- Provide accessibility/mobile/empty/error-state review checklists for each changed
  running screen; the user performs visual checks and confirms without screenshots.
- Produce setup/user guides, prototype limitations, final ERD/data dictionary,
  fictional demo accounts and a defense/demo script. Review GitHub commit history
  after student-approved pushes; screenshots are not required.
- Prepare environment/static/host settings for the selected demo deployment. Actual
  publishing and hosted upgrades are separate explicit actions; a local functional
  prototype remains the deliverable if hosting is outside the assignment.

Acceptance: the complete scenario checklist below passes; the student can start
and demonstrate the app from its guide; evidence and limitations match actual
behavior. Do not claim a PostgreSQL gate passed when only SQLite was available.

Commit: `test: verify complete clinic prototype and document demonstration setup`

## Updating the existing Supabase database

Supabase/PostgreSQL is the intended hosted prototype database. The roadmap includes
upgrading that existing database with Django migrations after its current state
has been inspected and the upgrade rehearsed. Editing pages, models, this plan or
the ERD, and committing/pushing Git changes do not by themselves migrate Supabase.
Page-only changes may need no schema migration; schema changes require migration
files committed with their feature. Django remains the migration authority for
the application tables; do not create a second competing SQL migration history.

Use an initial database checkpoint after Step 1 preparation if the hosted schema
lags behind the repository. Repeat the same process for later schema-changing
features when they are ready for hosted review; do not wait until Step 14 to
discover that application code and the hosted schema are incompatible.

1. Identify the intended Supabase project and database without exposing credentials.
   Inspect applied Django migrations with `showmigrations`, preview pending work
   with `migrate --plan`, and compare actual columns/constraints with migration state.
   Investigate drift from earlier manual SQL rather than blindly rerunning/faking
   migrations. Read-only inspection does not establish that an upgrade is safe.
2. Take a backup of existing application data/schema and prove it can be restored
   to an isolated PostgreSQL database. Do not assume a dashboard backup or staging
   branch is available on the account's plan. Keep dumps/credentials outside Git.
3. Restore representative existing data into disposable PostgreSQL staging, resolve
   legacy inconsistencies without inventing clinical information, and rehearse all
   pending migrations there. Verify IDs, account links, archives, row counts and
   key constraints before and after the upgrade.
4. Verify the migration connection, `btree_gist` and trigger privileges. Supabase
   documents direct connections for migrations; confirm an appropriate alternative
   if the environment cannot use that connection. Review app-table and archive
   grants/RLS separately from Django's role/object permissions. Never solve an
   access problem by granting broad public access to patient data.
5. Run PostgreSQL booking/concurrency/history tests against the disposable database
   only. Record the backup/restore result, migration list, reconciliation decisions,
   expected effects and any maintenance/write pause needed for the hosted upgrade.
6. Present that concrete migration report for the student's separately requested
   hosted-upgrade checkpoint. This planning request does not apply migrations now.
   `AGENTS.md` requires a verified backup and PostgreSQL staging rehearsal before
   applying migrations to the configured hosted database.
7. At the authorized checkpoint, use the reviewed migration files and intended
   hosted connection to apply `manage.py migrate`. Never run tests, recreate the
   database, delete migration history, use `--fake`, or drop clinic tables to make
   the command pass. Deploy the compatible application revision together with the
   schema upgrade so old/new code does not write incompatible data.
8. Verify applied migrations, schema/constraints, preserved records and core screens
   using authorized fictional test accounts. Do not place real health data into
   logs, screenshots or demonstration fixtures. Reconcile unverified legacy rows
   deliberately; an automatic schema upgrade cannot verify university membership.
9. If the upgrade fails, stop writes and follow the rehearsed recovery procedure.
   `register.0002` is intentionally irreversible through Django; its recovery is a
   verified backup restore, not an assumed reverse migration. Record the outcome
   and actual hosted migration state in this plan.

Database checkpoint commit, only when it changes tracked runbooks or validation
evidence: `docs: record verified Supabase prototype migration checkpoint`.
Applying a migration itself changes the database, not Git; it does not create a
new commit automatically. The exact migration commands/connection method and
checkpoint evidence will be prepared against the actual database state then.

References for implementation: [Django migration commands](https://docs.djangoproject.com/en/4.2/ref/django-admin/),
[Supabase connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres),
and [Supabase backup/restore guidance](https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore).

## Final demonstration checklist

- Student registers/signs in, updates permitted details, adds an emergency contact,
  books, cancels/rebooks, checks in, receives care and views released information.
- Nurse records vitals; assigned clinician documents diagnoses/treatment, issues
  a demonstration prescription/referral and finalizes the encounter.
- Faculty and Staff walk-ins receive documented care with no charge records.
- A Provider/Admin can receive care through a Patient profile in the same account;
  operational role access does not leak another patient's information.
- Admin prepares resources/terms, records a Student charge, exports it while Pending,
  demonstrates acknowledgment once and an audited void/reversal. No payment occurs.
- Concurrent/stale bookings and unauthorized URL/POST requests produce safe,
  understandable errors. Suspended accounts cannot continue using clinic features.
- Audit/report totals match the scenarios. Finalized clinical and posted financial
  history survive catalog, affiliation and account-activity changes.
- The app works with an empty database and fictional seeded data; desktop/mobile
  pages have useful loading-free server-rendered, empty, validation and error states.

## Validation and evidence per change

Use the existing venv interpreter even when shell activation is unavailable. Run
checks in an isolated tool process or dedicated test terminal; never accidentally
run tests/seed data against the configured hosted database.

```powershell
.\venv\Scripts\python.exe scripts\check_project.py
```

The runner forces isolated test settings for its children and does not change
your terminal configuration. Use `config.settings_local` for a persistent local
demo server. Start with tests for changed behavior; run broader regression checks
when shared auth, schema or cross-feature workflows change. Documentation-only
changes need link/diff review, not a new behavioral test.

For schema changes, include migration source and applicable ERD source/generated
artifacts together; keep populated legacy and metadata checks aligned. Do not edit
already applied migrations. Give the user a manual checklist for running UI changes
and wait for confirmation. Do not use Computer Use or request/capture screenshots.
Earlier capture checklists are superseded; visual review remains pending until
confirmed by the user.
Never include `.env`, passwords, real health information or database dumps in Git
or screenshots.

## Student review and Git handoff

Commands are run from `C:\Users\ADMIN\CITU_TeknoCare\TeknoCare`, the actual Git
repository. Current branch at review was `main`, with remote named `origin`. Never
assume a later branch/remote is identical: inspect status before each handoff.

The original planning change used the following handoff; Step 1's current changed
file list and Git commands are in [its handoff](step_1_verification.md):

```powershell
cd C:\Users\ADMIN\CITU_TeknoCare\TeknoCare
git status --short
git --no-pager diff -- AGENTS.md
git add -- AGENTS.md docs/development_plan.md
git diff --cached --check
git --no-pager diff --cached
git commit -m "docs: plan clinic pages Supabase upgrades and SQL demo removal"
git push origin main
```

Review the new plan in the editor before staging; ordinary `git diff` does not
display an untracked file. Review both files again with `git diff --cached` after
staging. A later handoff should use `git --no-pager diff` for tracked files and list new files
explicitly for editor review.

For every subsequent feature, provide concrete commands with the actual changed
file paths, actual branch and the step's final commit message. Do not leave
placeholders in a delivered handoff. Use explicit staging paths so unrelated work
is not swept into a commit. Review the staged diff before committing. If files
were already staged by the student, disclose them and avoid silently including
them. If push is rejected, inspect the divergence before suggesting merge/rebase;
do not recommend force push, hard reset, or discarding work.

## Progress and decisions

| Item | Status |
| --- | --- |
| Repository/ERD review and roadmap | Prepared November 18, 2026; awaiting student review |
| Step 0: SQL JOIN demonstration removal | Implemented November 18, 2026; see `docs/step_0_verification.md` for checks and review instructions |
| Step 1: reproducible local setup | Implemented November 18, 2026; isolated checks and HTTP smoke verification pass; student visual confirmation and remote CI pending |
| Step 2: authentication/provisioning/access | Implemented November 18, 2026; isolated tests/HTTP checks and ERD/legacy checks pass; user visual confirmation and PostgreSQL/hosted checks pending |
| Step 3: shared interface and role dashboards | Implemented and committed (`826a606`); user confirmed manual checks looked good before Step 4 |
| Step 4: clinic reference and personnel/provider administration | Implemented November 18, 2026; isolated/HTTP checks pass; user visual review and PostgreSQL staging pending |
| Steps 5–14 | Pending; include working page creation/changes; implement only the step requested next |
| Official ID formats, personnel/contracted provider identity, hours, fees, calendar | Unconfirmed; use documented fictional defaults until supplied |
| Configured hosted migration status | Not inspected or changed in this review |
| Existing Supabase upgrade | Planned through staged migration checkpoints; no hosted migration authorized or applied by this planning update |
| PostgreSQL staging/concurrency/restore | Not run in this review; required before claiming those guarantees |
| Verification handoff requirement | Provide exact commands/manual browser checks, expected outcomes and limits; no Computer Use or screenshots; wait for user visual confirmation before recording visual approval |

