# TeknoCare

CIT-University clinic school-project prototype built with Django 5.2 LTS,
server-rendered templates, CSS and JavaScript. The checked-in ERD has 22 entities
and 28 foreign keys. Most clinic screens are still planned; see the
[development roadmap](docs/development_plan.md).

## Start locally in PowerShell

Run commands from `C:\Users\ADMIN\CITU_TeknoCare\TeknoCare`, the folder containing
`manage.py`. Use Python 3.12. For a fresh checkout without a virtual environment:

```powershell
py -3.12 -m venv venv
```

The existing project already has `venv`; keep using it. Activation is optional
because these commands select the interpreter explicitly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py check --settings=config.settings_local
.\venv\Scripts\python.exe manage.py migrate --settings=config.settings_local
.\venv\Scripts\python.exe manage.py bootstrap_local_demo --settings=config.settings_local
.\venv\Scripts\python.exe manage.py runserver --settings=config.settings_local
```

The bootstrap command asks you to choose and confirm a password privately; typed
password characters are not displayed. Use a nontrivial password. It creates the
fictional local account `DEMO-ADMIN` with a hashed password. It never creates SQL
JOIN assessment samples. Repeating it reuses the same account without resetting
its password or overwriting conflicting records. If necessary, change this local
account's password with:

```powershell
.\venv\Scripts\python.exe manage.py changepassword DEMO-ADMIN --settings=config.settings_local
```

Open <http://127.0.0.1:8000/login/> and sign in as `DEMO-ADMIN` with the password
you chose. Stop the development server with **Ctrl+C**. A server that keeps the
terminal occupied while waiting for requests is running normally.

Local preview uses `db.sqlite3` in the project folder. It does **not** load `.env`
or use `DATABASE_URL`, even if your terminal or existing `.env` points to Supabase.
Consequently your old hosted accounts/data do not automatically appear locally.
`manage.py` defaults to local settings when no settings module is selected; use
the explicit `--settings` arguments shown here to override any inherited selection.
Keep existing `.env` unchanged. No `.env` file is required for local startup.

## Confirm Step 1 works

1. Installation finishes successfully. Confirm the framework with:

   ```powershell
   .\venv\Scripts\python.exe -m django --version
   ```

   Expected: `5.2.19`.
2. `check` reports **System check identified no issues**. `migrate` finishes with
   `OK` operations, or **No migrations to apply** when repeated.
3. Bootstrap reports **Created fictional local DEMO-ADMIN**, or **Reused local
   DEMO-ADMIN** on a repeat. A repeat preserves the password you originally chose.
4. Sign in at `/login/`. Expected: the dashboard greets **Prototype**. Open Profile
   and Settings; their forms and the top navigation should render normally. The
   existing interface is intentionally still simple at this setup checkpoint.
5. Click **Sign out** in the navigation. Expected: you return to `/login/`. Visiting
   `/dashboard/` afterwards redirects back to sign-in. This is a POST action with
   CSRF protection, required for compatibility with Django 5.2.
6. Open a second terminal in the project folder and run:

   ```powershell
   .\venv\Scripts\python.exe scripts\check_project.py
   ```

   Expected: dependency consistency, system checks, migration drift, feature tests,
   ERD agreement and populated legacy upgrade all pass. The final line reads
   **All isolated project checks passed. Supabase was not used.** One
   PostgreSQL-only test is skipped on SQLite; that skip is expected.
7. Review the diff before committing. If a command fails, stop there and share its
   command plus error text. Do not use `--fake`, delete the database, or run hosted
   migrations to work around a local setup error.

Every later feature handoff will include its own commands, browser actions,
expected results and a manual visual checklist before Git commit/push instructions.
The user checks the visuals and confirms in chat. Computer Use and screenshots
are not part of the development workflow.

## Confirm Step 0 works

The completed SQL JOIN school demo has been removed from the application. Its
[historical documents](docs/archive/sql_joins/README.md) remain available, while
clinic models, tables, migrations and existing data are preserved. No database
migration or dependency installation is needed for this removal.

With your venv active, stop any older development server with **Ctrl+C** and run:

```powershell
python scripts\check_project.py
python manage.py runserver --settings=config.settings_local
```

The checks should end with **All isolated project checks passed. Supabase was not
used.** In the browser, sign in and open Dashboard, Profile and Settings. Expected:
all three pages work and the navigation contains Dashboard, Profile, Settings and
Sign out, with no SQL joins entry. Sign out should still return to the login page.
Open `http://127.0.0.1:8000/joins/` directly: expected **404 / Page not found**,
whether signed in or signed out. This missing page is intentional.

Check the updated navigation on the three account pages following the
[Step 0 manual checklist](APPLICATION_SCREENSHOTS/step_0/README.md), then confirm
the results in chat; no screenshots are needed. The
[Step 0 handoff](docs/step_0_verification.md) records validation results and the
exact Git commands. Do not run the retired assessment seed/verification commands;
they are no longer installed. Existing historical sample rows are not deleted.

## Configuration boundaries

| Settings module | Purpose | Database / secrets |
| --- | --- | --- |
| `config.settings_local` | Local HTTP preview with debug enabled | SQLite file; fixed development-only key; no `.env`; normal password hashing |
| `config.settings_test` | Isolated automated checks | In-memory SQLite; fixed test key and fast test-only password hashing; no `.env` |
| `config.settings` | Explicit staging/hosted configuration | `.env` or process variables; required secret/database URL; debug defaults off |
| `config.settings_base` | Shared app/ERD configuration | Not a runnable environment; no database or secret |

All environments display clinic times in `Asia/Manila` and keep timezone-aware
timestamps. Email delivery is inactive locally and in tests. The local database
can be redirected to a separate SQLite file with `TEKNOCARE_LOCAL_DB_PATH`; parent
directories must already exist. This does not enable a PostgreSQL connection.

The standalone ERD verification scripts force test settings. The check runner also
forces test settings for each child process, regardless of your terminal settings.
It leaves your terminal and Supabase configuration unchanged. MD5 hashing is used
only in isolated test settings; local and hosted accounts use Django's normal
password hashing. Tests never need a real account, credential or medical record.

For automated local setup only, `bootstrap_local_demo --noinput` accepts a password
through `TEKNOCARE_DEMO_PASSWORD`. Do not commit it or put it in command arguments.
The command refuses environment-backed settings and all PostgreSQL databases.

## Django compatibility and migration history

Step 1 upgrades Django from 4.2.30 to 5.2.19 LTS. Django's
[supported-version table](https://www.djangoproject.com/download/) lists 4.2 as
unsupported and 5.2 LTS as supported through April 2028; its
[release notes](https://docs.djangoproject.com/en/5.2/releases/5.2/) include Python
3.12 support and require PostgreSQL 14 or newer. Validate the actual hosted
PostgreSQL version at the Supabase checkpoint.

The custom User remains `register.User`; login, Admin access, session invalidation,
password change and local bootstrap have regression coverage. The
[Django 5.0 compatibility notes](https://docs.djangoproject.com/en/5.2/releases/5.0/)
remove GET logout, so the navigation now uses a CSRF-protected button.

Populated SQLite rehearsal exposed an intermediate-primary-key issue in the
original profile migration under Django 5.2. The new
`profile.0003_profile_upgrade_compat` replacement performs non-key edits before
removing the old key, immediately followed by promotion of the user key. It reaches
the same final ERD without changing the original migration. Django's replacement
mechanism recognizes databases that already applied the original, so it does not
rerun those schema operations. The verification script checks both paths and
preservation of archived names/ages, IDs, links and timestamps. Keep both migration
files; do not delete the original or fake migration records.

## Hosted database and deployment

The [Supabase checkpoint runbook](docs/supabase_migration_checklist.md) covers
migration inventory, backup/restore, PostgreSQL staging and hosted verification.
Step 1 does not inspect or change the configured Supabase database.

`.env.example` is a credential-free template for the **environment-backed** settings.
Do not copy it over the existing `.env`. For a new hosted/staging environment,
provide a generated secret, the intended PostgreSQL URL, explicit allowed hosts
and `DEBUG=false`; retain `DATABASE_SSL_REQUIRE=true` for Supabase. Never commit
the resulting secret file. The template deliberately cannot connect as supplied.

WSGI/ASGI default to `config.settings` for deployment. Never deploy local/test
settings or the development server. Hosted settings enable secure session/CSRF
cookies when debug is off, so the hosted app needs HTTPS. After selecting a host,
configure its HTTPS/proxy behavior and static-file server, then run Django's
deployment checks. `STATIC_ROOT` points to `staticfiles`; the deployment process
must run `collectstatic` and serve that directory. A static root alone is not a
static-file server. No hosting provider or actual deployment is selected here.

## Automated checks and evidence

GitHub Actions runs the isolated SQLite check runner and a separate PostgreSQL 16
test job against a disposable service database. The CI password is deliberately
for that ephemeral service only. No Supabase secrets are required. CI starts after
the student pushes the commit; inspect **Actions → Clinic checks**. Both jobs
should be green. A configured workflow is not evidence that a remote run passed.
The PostgreSQL job exercises the existing database guards/exclusion test; it does
not yet prove concurrent-request behavior or upgrade the real hosted database.

The user reviews running screens and confirms the checklist results in chat.
No Computer Use or screenshots are required. `APPLICATION_SCREENSHOTS` retains its
historical folder name; its current checklist is text-only. Use fictional local
accounts for review. Preserve `BASELINE_COMMIT.txt` and legacy
archives. Step 0's SQL demonstration removal is implemented; its old page/link and
demo commands should no longer be available.
