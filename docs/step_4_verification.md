# Step 4: clinic reference and practitioner administration

Implemented November 18, 2026 after the user approved Step 3 and committed it as
`826a606`. The user reviews, commits and pushes this step. No Computer Use, browser
UI automation or screenshots are used. Step 4 visual approval remains pending.

## Pages and scope

Sign in as an Active Admin and open **Clinic setup** from navigation/dashboard.

| Page | URL | Available actions |
| --- | --- | --- |
| Clinic setup | `/clinic/` | Working links to the five setup areas |
| Departments | `/clinic/departments/` | Search/filter/page, add, edit, deactivate |
| Clinic rooms | `/clinic/rooms/` | Search/filter/page, add, edit, deactivate |
| Academic terms | `/clinic/terms/` | Search/filter/page, add, edit, open/close |
| Providers | `/clinic/providers/` | Search/filter/page, provision a login, attach eligible existing account, review/activate/deactivate |
| Personnel accounts | `/clinic/personnel/` | Search/filter/page, provision Faculty/Staff Patient accounts, change non-Admin access |

All management GET/POST requests require Active Admin authorization. Other roles
get 403, not just a hidden menu. Mutations are POST+CSRF and call authorized,
atomic feature services that audit successful writes. Validation and concurrent
uniqueness conflicts return form errors instead of partial account/profile writes.
There are no delete actions. Django admin remains a separate read-only utility.
Lists show operational data, not clinical notes or passwords, with ten results
per page, bound search/status filters, escaped content and empty states.

No schema migration, dependency update or ERD rerender is required. All 22
entities/28 FKs, original migrations, legacy archives and baseline remain intact.
The agent does not migrate the configured Supabase database or the existing local
database; HTTP checks use a separate ignored fictional SQLite file.

## Operational decisions and prototype limits

1. **IDs and identity:** Keep the existing 20-character string boundary, trim IDs
   while preserving case/leading zeros, and trim/lowercase emails. No official
   CIT-University personnel/provider ID format, email domain or enrollment system
   has been supplied. Do not generate IDs that claim to follow university policy.
2. **Provider data:** The ERD supplies account identity plus designation,
   optional license, optional specialization and clinical-active flag. No CV,
   credential upload, regulatory lookup, appointment hours or employment verifier
   is invented. Blank optional licenses become NULL; provided license text is
   retained without an invented format or fabricated number.
3. **Activation:** New Provider logins are Active accounts but clinically inactive,
   even if POST tries to set Admin role or activation. Explicit manual-review
   confirmation is required on activation/designation changes. Known designation
   and an Active Admin/Provider account are also required. The checkbox is an
   audited prototype attestation, not proof of professional qualification. Nurse
   activation never grants consultation-finalization or prescription rights.
4. **Existing accounts:** Attach an inactive Unverified Provider profile only to
   an existing Admin/Provider without one. Primary role, password and existing
   Patient profile are preserved. This supports an Admin who also practices or
   repairs an existing Provider missing its subtype; it cannot elevate a Patient
   login. Further Patient-profile intake/coexistence UI is Step 5.
5. **Personnel:** Faculty/Staff provisioning creates a Patient role/profile, not
   an Admin. Choose an active department or leave it unspecified; do not guess.
   Affiliation review is manual. Initial passwords are privately chosen/shared;
   ask the person to change theirs. No email or forced-change flag is implemented.
6. **Reference/history guards:** Referenced department codes, room locations,
   known provider designations and charged term identities/calendars cannot be
   silently rewritten through these services. Correct unknown legacy provider
   designation only after explicit review; other referenced corrections need a
   later reviewed workflow. Deactivating a department preserves patient links and
   affiliation, and prevents new personnel assignments to that department.
7. **Deactivation:** Room deactivation blocks unresolved Scheduled/Checked-In
   bookings, including overdue ones. Provider clinical deactivation also blocks
   Draft attending encounters. Otherwise active future slots are disabled in the
   same transaction. No visits, charges or bookings are deleted/reassigned.
   Reactivation does not reopen slots. Reconcile existing live work through the
   later scheduling/clinical workflow; do not delete records to bypass the guard.
8. **Account suspension:** Change account access is separate from clinical
   activation. Suspension revokes sessions immediately without deleting work or
   changing the clinical flag; unfinished bookings need follow-up. Reactivation
   does not resurrect old sessions. Admin/self access changes require the trusted
   operator, not this page. Normal new active slots/encounters and booking recheck
   current account/provider eligibility, including stale related-object cases.
9. **Terms/finance:** Use consecutive `YYYY-YYYY`, a supplied/fictional semester
   label and valid date range. Official term dates/labels/fees are not assumed.
   Open/closed means eligibility for later tuition charge actions, never payment
   status. Closing preserves charges and allows later audited reversals. Setup
   creates no charge, payment, receipt or university acknowledgment. Faculty/Staff
   care remains free, with no zero-charge placeholders.

Actual patient intake/allergies, slot creation, booking, triage, clinical notes,
prescriptions and charge pages remain their later steps. Raw SQL/bulk writes can
bypass application guards and need restricted database access. Booking now locks
provider account, provider, room and slot in a consistent order and avoids a
nullable outer-join FOR UPDATE, but SQLite is not evidence of PostgreSQL locking/
concurrency correctness. Staging and hosted backup/restore gates remain separate.

## Automated verification

From the repository folder, with your venv active:

```powershell
python scripts\check_project.py
python manage.py collectstatic --noinput --dry-run --verbosity 0 --settings=config.settings_local
```

Agent result: **137 tests passed and one PostgreSQL-only test skipped** (138
discovered). Dependencies, system checks, migration drift, all tests, 22-entity/
28-FK ERD agreement, populated legacy upgrade, static dry-run and diff whitespace
checks pass. The runner ends **All isolated project checks passed. Supabase was
not used.**

New tests cover every management page's role/CSRF/method boundaries, shared dark
layout, GET read-only behavior, reference validation/duplicates, filter/pagination
and escaping, provisioning injection/rollback, active departments, activation
review, optional licenses, Admin profile attachment, Nurse limits, stale suspended
providers, history/deactivation guards, term closure/reversal and audit rollback.

A real local HTTP smoke check passes for all five setup areas, reference creation
and editing, invalid term/provider activation feedback, Faculty/Provider logins,
Admin profile attachment, suspension/session denial, themes and static assets.
No charges are created in that smoke check. It uses only fictional isolated data;
it is not a visual review or a hosted/PostgreSQL staging result.

## Start and manually confirm

Stop the old server with **Ctrl+C**, then run:

```powershell
python manage.py runserver --settings=config.settings_local
```

No new Step 4 migration is needed on your working Step 3 database. For a fresh
local database follow README migration/bootstrap setup first, explicitly using
local settings. Do not run hosted migrations just to preview these pages.

1. **Admin navigation:** Sign in as `DEMO-ADMIN`; open Clinic setup. Expect five
   working sections, with light/dark theme matching your saved setting. Lists
   may initially show an honest empty state; they are not seeded with university
   reference data. Existing records remain available.
2. **Department:** Add `FIC-DEPT` / `Fictional Department`, Active. Expect a success
   notice and a list row. Try the same code again: expect an error, not a second
   row. Use another clearly fictional code if you already used this example.
3. **Room:** Add campus `Fictional Campus`, building `Demo Building`, room `FIC-01`,
   Active. Expect a success row and duplicate-location rejection. For an unused
   room, uncheck Active and save: expect Inactive with the same row retained;
   reactivation is another edit, not a new row. Existing referenced rooms may
   correctly reject location changes or deactivation due to unresolved bookings.
4. **Term:** Add fictional `2026-2027` / `Demo Term`, dates `2026-08-01` through
   `2026-12-31`, Open for charges. Expect Open. Invalid/nonconsecutive years or
   an end before start must fail. Close it: expect Closed, no payment or charge.
   These dates are examples, not the official university calendar.
5. **Faculty/Staff:** Add a fictional account such as `FIC-STAFF-001`, email
   `fic-staff@example.invalid`, Staff and the active fictional department. Choose
   a strong private password. Expect a personnel row with Active access. Sign in
   as that person in a separate browser/private window: expect Patient workspace
   with Staff affiliation, not Admin privileges. Repeat with Faculty if desired.
   Inactive departments must not appear for new assignments.
6. **Provider creation:** As Admin add `FIC-PROV-001`, email
   `fic-provider@example.invalid`, fictional name and a privately chosen strong
   password. Leave license/specialization blank and use Unverified initially.
   Expect the review page with clinical activation unchecked; the person can
   sign in to account pages but cannot practice based on that login alone.
7. **Provider review:** Try activating Unverified with review confirmed: expect
   a form error. For the fictional demonstration, choose Physician/Dentist/Nurse,
   check Clinically active but omit review confirmation: expect another error.
   Then explicitly confirm the prototype review and save: expect Active clinical
   flag with Active account. Unknown license may remain blank. This does not
   establish real credentials or enable unfinished clinical screens. For Nurse,
   the Provider dashboard must still describe the prescribing/finalization limit.
8. **Deactivate/suspend:** On that new provider, clear Clinically active and
   save: expect Inactive while account sign-in still works. Change account access
   to Suspended with confirmation: an existing session must return to sign-in on
   its next request. While access is still Suspended, attempting clinical activation
   must fail. Then reactivate account access: new sign-in works, old sessions
   must not return. Clinical activation must not change just from suspension.
   No history should disappear.
9. **Existing Admin-as-provider (optional):** Attach existing account should list
   only eligible Admin/Provider accounts lacking a Provider row. Selecting your
   fictional Admin creates an inactive Unverified profile, preserves Admin role
   and does not activate clinical rights. Do this only if useful for your demo;
   attaching is not deletion/replacement of an existing profile.
10. **Filters/pagination/security:** Search your fictional code/name; toggle status
    filters and Reset filters. With over ten matching rows, Next/Previous must keep
    filters; otherwise pagination is correctly absent. As a Patient or Provider,
    open `/clinic/` and `/clinic/providers/` directly: expect 403. Anonymous users
    should be asked to sign in. There should be no Delete actions anywhere here.
11. **Visual/regression:** Check a list, empty state and creation/review form at
    desktop/narrow width and both themes. Wide tables should scroll within their
    region; controls should wrap and stay usable with keyboard/zoom. Error summaries,
    labels and success notices must be readable. Existing profile/preferences,
    password flows and POST sign-out should work; `/joins/` remains intentionally
    404. Confirm results in chat without screenshots.

Live-booking/Draft deactivation blocks, historical charged-term protection and
audit-failure rollback have automated fixtures; there are no manual clinical/
booking pages yet to generate those cases. Do not alter/delete database history
to force a visual test. If a check fails, share the page/action and error text,
not passwords or private records. Step 4 manual approval is pending your response.

## Commit and push after approval

From `C:\Users\ADMIN\CITU_TeknoCare\TeknoCare`, branch `main`, remote `origin`:

```powershell
git status --short
git --no-pager diff
git add .
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "feat: manage clinic reference data and practitioner accounts"
git push origin main
```

Review new files in your editor or via `git --no-pager diff --cached`. Stage only
this step's reviewed changes; keep `.env`, databases, credentials, venv and
unrelated work out of Git. LF/CRLF informational notices are not failed tests.
Stop before committing if checks fail. No Git write is performed by the agent.
