# Step 14 prototype setup and review

## Start a clean local demonstration

With your venv active, open PowerShell in the folder containing `manage.py`.
Stop any earlier local server with **Ctrl+C** in its terminal.
Use a separate SQLite file so you can keep earlier practice records and repeat
the demonstration with a fresh database when needed.

```powershell
New-Item -ItemType Directory -Force tmp | Out-Null
$env:TEKNOCARE_LOCAL_DB_PATH = 'tmp/final-demo.sqlite3'
python manage.py migrate --settings=config.settings_local
python manage.py bootstrap_local_demo --workflow --settings=config.settings_local
python manage.py runserver 127.0.0.1:8000 --settings=config.settings_local
```

Open [the local sign-in page](http://127.0.0.1:8000/login/). The bootstrap asks
you for one private password for the new fictional accounts. On repeat it
preserves existing credentials and records. If you have already changed a
reserved demo fixture, use a new SQLite filename for a clean rehearsal.
Stop the server with **Ctrl+C**. Clear this terminal's demo path afterwards with
`Remove-Item Env:TEKNOCARE_LOCAL_DB_PATH`.

| University ID | Account and role in the demo |
| --- | --- |
| `DEMO-ADMIN` | Clinic Admin and a secondary Staff Patient profile |
| `DEMO-STUDENT` | Student Patient |
| `DEMO-FACULTY` | Faculty Patient |
| `DEMO-STAFF` | Staff Patient |
| `DEMO-NURSE` | Provider, Nurse |
| `DEMO-DOCTOR` | Provider, Physician |
| `DEMO-DENTIST` | Provider, Dentist |

The seed prepares room **DEMO-CLINIC**, an open **Prototype term** and
fictional diagnosis and medication entries. As **Clinic Admin**, add a slot
for **DEMO-DOCTOR** in **Dashboard → Clinic availability**. For a continuous
booking-to-care demo, use a start later today in Manila time and an end at least
30 minutes after the start.

## Three browser checks

1. **Student Patient (`DEMO-STUDENT`).** Open **My appointments → Book an appointment**,
   pick the slot and book it. Cancel, then book it again. Expect one current
   booking and the first booking marked **Canceled** in history.
2. **Clinic Admin, Provider (Nurse), then assigned Provider (Physician).** In
   **Reception queue**, check in the Student and open the encounter. As Nurse,
   record a vital. As Physician, save the consultation and finalize the
   encounter. As the **Student Patient**, open **My visit summaries** and confirm
   the visit appears. For the full prescription and referral path, use the
   [demo script](prototype_demo.md).
3. **Clinic Admin (`DEMO-ADMIN`), then Faculty or Staff Patient.** In
   **Tuition charges**, create and simulate posting a Student charge and verify
   the **Posted** amount in **Operational reports**. From the Admin dashboard,
   open **My tuition charges** and confirm the Staff profile can open its own
   page. As Faculty or Staff, confirm the free-care message and verify that
   `/clinic/reports/` returns **403**.

## Layout and accessibility review

At desktop width and a narrow window, check that headings and labels are
readable, actions remain reachable with **Tab**, focus is visible and wide
tables scroll within their regions. Check these pages as the account used for
each task.

| Screens | State to verify |
| --- | --- |
| Login, registration, dashboard, patient details | Invalid fields show linked error messages. Each role sees its available actions. |
| Appointment booking, availability and reception | Empty results explain the next action. An unavailable slot shows a recoverable message. |
| Clinical encounter, prescriptions and referrals | Nurse actions remain visible. Required consultation fields and confirmation errors are readable. |
| Patient summaries, print previews and tuition history | An empty list gives a clear result. Print previews retain the prototype label. |
| Admin charge screens, audit history and operational reports | Filters keep their values during paging. Tables scroll at narrow width. Pending, Posted and Voided labels remain readable. |

## Local verification and Git handoff

```powershell
python scripts/check_project.py
git status --short
git add .
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "test: verify complete clinic prototype and document demonstration setup"
git push origin main
```

The check runner uses isolated SQLite and leaves your demo file alone. The
**Clinic checks** workflow also runs on a disposable PostgreSQL server after
push. Check that the working tree contains only the Step 14 changes before
staging.

## PostgreSQL rehearsal evidence

The project checks passed with 224 tests on SQLite and 225 tests on
PostgreSQL. SQLite skipped its nine PostgreSQL-only tests. PostgreSQL
skipped eight tests for the SQLite-only demo bootstrap. The PostgreSQL run
covered simultaneous booking, duplicate finalization, duplicate issue and
duplicate simulated posting. All seven local demo accounts also signed in
successfully in a fresh SQLite setup.

On a disposable PostgreSQL 16.16 cluster, the original migration state was
populated with fictional accounts, an appointment, a medical record, profile
and settings data, and audit and support history. The cluster was shut down
before its data directory was backed up. The backup started successfully as
a separate cluster on a different loopback port.

The restored copy still had the original IDs and migration state before upgrade.
The upgrade preserved appointment and account links, visit timestamps, profile
and settings data, audit actors and retired-field archives. Missing affiliation,
room and provider designation stayed unverified. The upgrade also recognized
the original profile migration and verified `btree_gist` plus both slot
exclusion constraints. [PostgreSQL file system backup guidance](https://www.postgresql.org/docs/16/backup-file.html)

This rehearsal used fictional records. The hosted checkpoint still needs a
verified Supabase backup and restore, a representative data review and approval
for the actual migration.

## Deployment boundary

The selected presentation setup is the local loopback server. It serves the
project CSS and JavaScript directly from `static/`. For a separately chosen
hosted environment, prepare `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`,
`DEBUG=false`, and TLS using the intended host's settings. Run
`python manage.py collectstatic --settings=config.settings --noinput` as part
of that deployment and serve the generated `STATIC_ROOT` through the host.
Use the [Supabase migration checklist](supabase_migration_checklist.md) for
backup, access review and the planned schema update.
