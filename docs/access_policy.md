# Prototype account and access policy

Implemented in Step 2, November 18, 2026. These are conservative school-project
rules, not confirmed CIT-University operating policy. Clinical/reference screens
are still scheduled for later steps. Never infer permission just from a visible
link or a related patient/provider row.

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
| Manage accounts, reference data, tuition charges, audit viewer | No | No | No | Yes |
| Book appointment | Own Patient profile | Own Patient profile if present | Own Patient profile if present | Active Patient profile target |
| Cancel appointment | Own future Scheduled booking, no encounter | Same ownership rule | Same ownership rule | Same state rules, any patient |
| Manage provider availability | No | Own provider | Own provider | Any provider; scheduling validation still required |
| Patient operational details | Self | Assigned Draft encounter or live/current-or-future booking | Same assignment, or today's Draft triage queue | Operational access, not full clinical notes |
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
  An account-management page will use the service in a later step.
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

## Limits before any real deployment

This prototype lacks login/reset throttling, MFA, verified enrollment/personnel
identity, email recovery and production recovery operations. Keep demonstrations
local and fictional; do not expose it publicly or use real health information.
Database-owner/raw SQL access can bypass application permission checks. PostgreSQL
grants, Supabase exposure/RLS and representative migration/concurrency behavior
require the separate staging/backup checkpoint. SQLite tests are not evidence of
hosted deployment or production security certification.
