# Step 3: shared interface and role dashboards

Implemented November 18, 2026 after the Step 2 commit (`7d41a70`). The user reviews,
commits and pushes. No Computer Use, browser UI automation or screenshot capture
is used. Visual approval remains pending until the user confirms in chat.

## What changed

- All seven clinic page templates now extend one base: login, registration,
  dashboard, profile, preferences, password change and Admin-assisted reset.
- Shared navigation, messages, error summaries, form controls, keyboard focus,
  responsive layouts and light/dark styles replace duplicate CSS and stale scripts.
- Settings now applies the saved account-specific theme across signed-in clinic
  pages and future sign-ins. Public signed-out pages default to light.
- Patient, Provider and Admin dashboards show own-account information and only
  working tasks. Unfinished clinic functions are clearly described, not linked.
  Provider inactivity/unverified designation and Nurse restrictions are explicit.
- Profile copy/controls now match phone/address/bio ownership; Profile/Settings
  saves show confirmation. Email delivery is explicitly unavailable even when
  its saved preference is enabled.
- Reusable table, empty-state and filter-preserving pagination patterns are ready
  for later list pages. No new clinical/reference list or workflow is added here.

No model, ERD, migration or dependency changes are required. The configured
Supabase database, existing local database, original migrations, legacy archives
and baseline file are unchanged by this work. Django admin stays read-only and
retains its own framework theme controls, separate from the clinic preference.

## Automated checks

Agent result: **107 tests passed, one PostgreSQL-only test skipped** (108
discovered). The full isolated runner, static collection dry-run, local HTTP
smoke checks and `git diff --check` pass. Git's LF/CRLF notices are informational.
Manual visual/keyboard review and PostgreSQL/hosted rehearsal are not claimed.

From `C:\Users\ADMIN\CITU_TeknoCare\TeknoCare` with your venv active:

```powershell
python scripts\check_project.py
python manage.py collectstatic --noinput --dry-run --verbosity 0 --settings=config.settings_local
```

Expected: dependencies, system checks, migration drift, all feature/security tests,
22-entity/28-FK ERD agreement and populated legacy upgrade pass. One PostgreSQL-only
test is intentionally skipped on SQLite. Final runner line:
**All isolated project checks passed. Supabase was not used.** The static dry-run
should finish successfully without copying files. No new migration should appear.

Tests also cover Patient/Provider/Admin working links, own-data boundaries,
unknown affiliation, secondary profiles, inactive/unverified Provider and Nurse
states, saved theme persistence/isolation, messages, escaped content, valid form
label/error/help references, CSRF, pagination filters/boundaries and palette pairs.
Real HTTP smoke checks use a separate ignored fictional SQLite database and
normal local password hashing to exercise all three role dashboards, theme
switching across pages/re-login, profile errors/success, role denials, static
assets, email notices and the intentional `/joins/` 404. These checks do not
inspect visuals or certify complete accessibility/production security.

## Start for your manual review

Stop the previous server with **Ctrl+C**, then run:

```powershell
python manage.py runserver --settings=config.settings_local
```

No Step 3 migration is needed. If this is a fresh checkout/database rather than
your previously working Step 2 setup, follow the README's local migration/demo
bootstrap instructions first. Do not switch to hosted settings for these checks.
If old styling is cached, refresh with **Ctrl+F5** after restarting the server.

### Check these actions and expected results

1. **Public pages:** Open `/login/` and `/register/` while signed out. Expect the
   teal/blue-green style, readable labels, working cross-links, prototype footer
   and light theme. Try incorrect login credentials or a weak registration
   password: expect a clear summary and field errors without exposing passwords.
2. **Admin dashboard:** Sign in as `DEMO-ADMIN`. Expect **ADMIN WORKSPACE**, your
   own ID/role/status, and working Profile, Settings, Change password, Reset
   account password and Inspect accounts tasks. Inspect accounts opens read-only
   Django admin. There must be no fake appointment/visit totals or dead clinical
   links. Django admin's own theme controls are separate and unchanged.
3. **Save and retain dark mode:** In Settings, enable Use dark mode and save.
   Expect a confirmation and dark background/cards/inputs. Visit Dashboard,
   Profile, Change password and Admin reset: all clinic pages should stay dark,
   with readable text/errors. Sign out: login returns to light. Sign in as the
   same account: dark returns. Disable dark mode and save: light returns.
4. **Account isolation:** Use a fictional Student account, registering one if
   necessary. Expect **PATIENT WORKSPACE**, their own ID/affiliation and only
   Profile, Settings and Change password tasks. It must not inherit another
   account's saved dark preference or show Admin tasks. `/login/reset-password/`
   must still give 403. Different windows signed in as the same account share
   the saved theme on their next page request, not a live browser broadcast.
5. **Profile and preferences:** Save a fictional contact phone/address/bio.
   Expect a success notice and persisted values on reload. There are no name,
   age or birth-date editing controls. Saving email preference on/off must persist
   and explain that delivery is unavailable; no email should be sent. Do not put
   real medical information in the bio or these prototype forms.
6. **Password form errors:** Try a wrong current password with otherwise valid
   replacement values. Expect an error summary that receives focus, a working
   link to the affected field, visible field error and no password change. These
   forms retain Step 2's session/reset behavior and CSRF protection.
7. **Keyboard and layout:** Use Tab/Shift+Tab on login and a signed-in page.
   The skip link and visible focus outline should work, labels should activate
   their controls, and all links/buttons should remain reachable. Check desktop,
   a narrow window around phone width, and browser zoom. Navigation should wrap,
   dashboard cards should stack and forms/messages must not overlap or overflow.
   Repeat a form/error check in both themes. JavaScript is only an error-focus
   enhancement; saving forms and themes still works without it.
8. **Provider (if you already have a fictional account):** Expect **PROVIDER
   WORKSPACE**, own designation/activation and account tasks, with no Admin
   actions or other patients' details. Inactive/unverified profiles explain that
   activation is needed. Provider/Nurse combinations and secondary Patient
   profiles are covered automatically; do not edit database roles or invent
   credentials just to force a manual preview. Provisioning UI is Step 4.
9. **Regression:** Sign out still returns to login; `/joins/` is intentionally
   404. No SQL demo entry reappears in navigation.

Confirm the results in chat, or share the page/action and error text if a check
fails. No screenshots are required. Visual, keyboard and browser accessibility
review is not marked passed until you confirm. PostgreSQL CI/hosted backup and
migration rehearsal remain separate gates, not outcomes of local SQLite tests.

## Commit and push after approval

```powershell
git status --short
git --no-pager diff
git add .
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "feat: add shared clinic interface and role dashboards"
git push origin main
```

Review that all staged changes belong to Step 3. Deletions of old duplicate CSS
and tiny feature scripts are intentional; the new shared stylesheet/script replace
them. Review new files in your editor or with `git --no-pager diff --cached`.
Never stage `.env`, venv, databases, credentials or unrelated edits. Stop before
committing if an automated/manual check fails. Do not force push to bypass a
rejected push; inspect the divergence first.
