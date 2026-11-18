# Step 0 verification and Git handoff

Implemented November 18, 2026, after Step 1 at the student's request. The completed
school SQL JOIN demo is removed from the application. No database migration or
dependency installation is needed for this change.

## Changes

- Removed `apps.joins` from installed apps and deleted its source, seed/verification
  commands and 15 demo-only tests.
- Removed `/joins/`, its navigation link, both templates and its stylesheet.
- Moved the four assessment documents/SQL examples into
  [the historical archive](archive/sql_joins/README.md), with prominent archive
  notices. Historical references are not active setup instructions.
- Updated active documentation, roadmap progress, developer instructions and the
  earlier screenshot checklist to reflect the removal.

Clinic model/migration files, the ERD and `BASELINE_COMMIT.txt` are unchanged. No
existing sample rows, accounts, clinical history or `legacy_*` archives were
deleted. Supabase was not accessed. The demo owned no clinic tables; removing it
does not remove Patient, Provider, Slot, Appointment or their data.

## Verification completed

| Check | Result |
| --- | --- |
| Full isolated check runner | Passed: dependencies, Django checks, migration drift, tests, ERD and legacy upgrade |
| Remaining tests | 53 discovered: 52 passed, one PostgreSQL-only test skipped on SQLite |
| Test count change | The 15 completed assessment tests were removed; clinic/account tests remain |
| ERD agreement | All 22 entities and 28 relationships match |
| Populated legacy upgrade | Passed, including already-applied profile replacement recognition |
| Fresh local preview migration | Existing migration chain applied successfully without the retired app |
| Real HTTP account/auth check | Login, dashboard, profile, settings, Admin, registration and POST sign-out work |
| Real HTTP navigation check | Dashboard/profile/settings omit the retired link and retain clinic navigation |
| Retired URLs/assets | `/joins/` returns 404 signed in and signed out; old demo CSS returns 404 |
| Command registry | Neither retired seed nor verification command is installed |
| Source reference scan | No retired app imports, URL names, template names or commands remain in runtime source |
| Database schema/baseline source | No model, migration or baseline-file changes |

The agent's HTTP preview used ignored `tmp/step0-preview.sqlite3` on port 8766
with fictional data, separate from your normal local database. The preview server
was stopped afterwards. Existing hosted/current-local data was not used for tests.

## Confirm it yourself

With the venv already active, run from the folder containing `manage.py`:

```powershell
python scripts\check_project.py
python manage.py runserver --settings=config.settings_local
```

Expected final check message: **All isolated project checks passed. Supabase was
not used.** Stop any old server with **Ctrl+C** before starting the updated one.
Do not recreate the local database; use the account you already created in Step 1.

1. Open `http://127.0.0.1:8000/login/` and sign in with your local account.
2. Open Dashboard, Profile and Settings. Each should load normally, with no SQL
   joins link. Dashboard/Profile/Settings/Sign out should still be available.
3. Open `http://127.0.0.1:8000/joins/` directly. Expect **404 / Page not found**.
4. Sign out and repeat the old URL check. It should still be unavailable; opening
   `/dashboard/` should instead redirect to sign-in.
5. Follow the [manual visual checklist](../APPLICATION_SCREENSHOTS/step_0/README.md),
   including desktop/narrow widths, then confirm the results in chat. No screenshots
   are needed.

The user has requested no further Computer Use and no screenshots. Visual review
is performed by the user and remains pending until they confirm the checklist.
Automated HTTP checks do not replace that confirmation.
GitHub's PostgreSQL job will run after push; this step does not claim staging or
concurrent-request verification.

## Git commands after review

These commands stage this checkpoint's source removals, archived documents and
review instructions. `--no-pager` avoids the terminal diff pager. Inspect status
and the staged diff before committing, especially if other work has appeared.

```powershell
cd C:\Users\ADMIN\CITU_TeknoCare\TeknoCare
git status --short
git add -- config/settings_base.py config/urls.py templates/includes/navigation.html
git add -A -- apps/joins templates/joins static/css/joins
git add -A -- docs/sql_joins_activity.md docs/sql_joins_examples.sql docs/sql_joins_verification.md docs/sql_joins_video_script.md docs/archive/sql_joins
git add -- AGENTS.md README.md docs/development_plan.md docs/erd/model_implementation.md docs/erd/design_review.md
git add -- docs/step_0_verification.md docs/step_1_verification.md APPLICATION_SCREENSHOTS/step_1/README.md APPLICATION_SCREENSHOTS/step_0
git diff --cached --check
git --no-pager diff --cached --stat
git --no-pager diff --cached
git commit -m "chore: remove completed SQL join demonstration"
git push origin main
```

The student performs the commit/push after review; the agent has not staged or
committed this change. After pushing, confirm both jobs under **Actions → Clinic
checks** pass. If a check fails, share the command/job and error output before
continuing to Step 2.
