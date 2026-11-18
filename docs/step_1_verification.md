# Step 1 verification and Git handoff

This is the historical Step 1 handoff. Step 0 has since removed the completed SQL
assessment; use [the Step 0 handoff](step_0_verification.md) for the current change.
The test counts and browser limitations below describe Step 1's original review.

Implemented November 18, 2026. Follow [README confirmation steps](../README.md#confirm-step-1-works)
before approving this checkpoint. Every later feature handoff must likewise give
the student commands, browser actions and expected results before commit/push.

## What changed

- Isolated local SQLite and in-memory test settings, separate from environment-backed
  Supabase configuration; `manage.py` defaults locally unless explicitly selected.
- Credential-free environment example, ignored local databases/secret variants,
  Manila display time, static collection path and deployment boundary documentation.
- Django 5.2.19 LTS with a data-preserving profile replacement migration. Original
  migrations and the final 22-entity/28-relationship ERD remain unchanged.
- Local fictional Admin bootstrap with private password entry, conflict refusal,
  repeatability and a custom-user-compatible password change command.
- POST+CSRF sign-out button with shared navigation styling; this small compatibility
  change was brought forward from Step 2 because Django 5.2 removed GET logout.
- One-command project validation, SQLite and disposable PostgreSQL GitHub jobs,
  the Supabase migration checkpoint runbook and persisted confirmation instructions.

`requirements.txt` is now UTF-8 text instead of UTF-16 so standard repository
editing tools can maintain its pins. Git may show the original as a binary diff;
the dependency change is Django 4.2.30 to 5.2.19. Other pins are preserved.

## Completed verification

| Check | Result |
| --- | --- |
| Installed framework | Django 5.2.19 on the existing Python 3.12.10 venv |
| Dependency consistency | `pip check` passed |
| Targeted setup/auth tests | 15 passed |
| Full isolated suite | 68 discovered: 67 passed, one PostgreSQL-only test skipped |
| System/migration drift checks | No system issues; no model changes detected |
| ERD comparison | All 22 entities and 28 FK relationships match |
| Populated legacy SQLite upgrade | Preserved IDs, links, timestamps, profile/settings, actors and archives |
| Already-applied original profile migration | Recognized without rerunning replacement schema operations |
| Fresh local SQLite migration | All migrations applied successfully on isolated preview database |
| Demo bootstrap repeat | Reused account without resetting password or adding duplicates |
| Real local HTTP smoke test | Login, dashboard, profile, settings, Admin, navigation CSS and CSRF sign-out passed |
| Local/test boundary | Tests prove hosted URL/config values cannot redirect local/test settings |
| Git diff whitespace | Passed |

The smoke preview used `tmp/step1-preview.sqlite3` on port 8765. It is ignored,
contains fictional data only, and is separate from the student's normal local
`db.sqlite3`. Use the README commands to choose your own local Admin password.

## Still to confirm

- Student visual checks: confirm the current manual checklist in chat. The user
  has superseded the earlier screenshot requirement; no Computer Use or screenshots
  are requested. Automated checks do not establish visual approval.
- GitHub CI: prepared, not remotely run yet. After pushing, inspect
  **Actions → Clinic checks**; both jobs should pass. Report a failed job's log.
- Supabase schema/version, backup/restore, PostgreSQL staging and concurrency
  remain unverified. No hosted connection or migration occurred in this step.
- Step 0 was pending at this checkpoint because the student requested Step 1 first.
  It has since removed the assessment app in its own change; do not expect the
  old SQL demo page/link to exist in the current app.

## Commit after review

Run from the actual repository root. `--no-pager` prevents the diff viewer from
occupying the terminal. These paths cover the Step 1 source/docs changes; no
secret, SQLite database or generated static directory should be staged.

```powershell
cd C:\Users\ADMIN\CITU_TeknoCare\TeknoCare
git status --short
git add -- .env.example .gitignore AGENTS.md README.md manage.py requirements.txt
git add -- config/settings.py config/settings_base.py config/settings_local.py config/settings_test.py config/tests.py
git add -- apps/register/management apps/register/test_local_demo.py apps/login/tests.py apps/profile/migrations/0003_profile_upgrade_compat.py
git add -- scripts/check_project.py scripts/verify_erd_models.py scripts/verify_erd_upgrade.py .github/workflows/checks.yml
git add -- templates/includes/navigation.html static/css/home/home.css static/css/profile/profile.css static/css/includes/navigation.css
git add -- docs/development_plan.md docs/erd/model_implementation.md docs/supabase_migration_checklist.md docs/step_1_verification.md APPLICATION_SCREENSHOTS/step_1/README.md
git diff --cached --check
git --no-pager diff --cached --stat
git --no-pager diff --cached
git commit -m "chore: establish reproducible prototype development setup"
git push origin main
```

No screenshot files are required under the user's current preference. If a new unrelated file or
already-staged change appears, inspect it separately before committing. The agent
has not staged, committed, pushed or changed the student's branch.
