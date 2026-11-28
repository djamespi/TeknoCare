# TeknoCare

TeknoCare is a CIT-University clinic prototype built with React, Django, and
PostgreSQL on Supabase. Students book visits and view their records. Providers
manage schedules and document care. Clinic administrators manage accounts,
clinic reference data, audit history, and simulated student tuition charges.

## Run the portal against the sample database

Install Python 3.12 and Node.js 24. From the directory containing manage.py,
create a virtual environment if needed and install the dependencies.

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm.cmd --prefix frontend ci
```

Use the project's existing private .env, or use .env.example to configure a
new one. Point DATABASE_URL at the Supabase database named teknocare_make_demo.
Keep the connection URL and secret key outside version control.

```powershell
npm.cmd --prefix frontend run build
$env:DEBUG = 'true'
$env:ALLOWED_HOSTS = '127.0.0.1,localhost'
$env:DATABASE_SSL_REQUIRE = 'true'
python manage.py runserver 127.0.0.1:8010 --settings=config.settings_make_demo
```

Open [the portal](http://127.0.0.1:8010/portal/). Sample sign-in IDs include
23-10481 (student Bianca Manalaysay), MD-1048 (Dr. Mara Villareal), and
ADM-0001 (clinic administrator). Use the sample password set when the database
was populated.

## Run locally with SQLite

```powershell
python manage.py migrate --settings=config.settings_local
python manage.py bootstrap_local_demo --settings=config.settings_local
python manage.py runserver --settings=config.settings_local
```

The bootstrap command prompts for the password for the local DEMO-ADMIN
account. Open [the local portal](http://127.0.0.1:8000/portal/) after building
the frontend. Local and test settings ignore DATABASE_URL.

## Page and feature layout

| Location | Responsibility |
| --- | --- |
| frontend/src/features/ | One folder per portal page, with page-specific components and assets alongside it. Registration appears within sign-in and has its own feature folder. |
| frontend/src/App.tsx | Routes and role-specific entry points. |
| frontend/src/components/ and frontend/src/data/ | Shared UI, session state, API transport, and types. |
| apps/<feature>/ | Django models, migrations, services, forms, routes, views, tests, feature templates and styles, and portal action handlers. |
| apps/portal/ | Portal shell, role-scoped read model, and JSON action dispatch. |
| templates/ and static/ | Shared template layout, includes, branding, and styles. The Vite build writes to static/portal/. |

For example, booking starts in frontend/src/features/book-visit/. Its actions
call the appointment services in apps/appointments/, which also owns the
fallback Django booking pages. The clinical chart and provider queue follow
the same pattern with apps/clinical/. Shared services support related pages
without duplicating business rules.

## Verify and deploy

```powershell
python scripts/check_project.py
npm.cmd --prefix frontend run check
npm.cmd --prefix frontend run build
```

The Python runner uses isolated SQLite settings and checks migration drift,
feature behavior, the schema contract, and an upgrade from populated legacy
data. CI also runs against disposable PostgreSQL. For a hosted deployment,
build before running collectstatic and serve the collected files over HTTPS.
See the [account access policy](docs/access_policy.md).
