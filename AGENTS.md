# TeknoCare project guide

Reviewed on 2026-10-12 against the local working tree. This is a starting point
for future work; check the relevant source files and Git status before making
changes. The working tree includes the dashboard/profile/settings fixes from
this conversation, which have not been committed as of this review.

## Purpose and stack

TeknoCare is a university clinic web application. Current public registration
creates patient accounts; the data model also includes providers and admins.

- Python/Django application, with Django 4.2.30 pinned in `requirements.txt`.
- The existing Windows `venv` was created with Python 3.12.10.
- Server-rendered Django templates, plain CSS, and small vanilla JavaScript files.
- PostgreSQL hosted on Supabase, accessed through Django's ORM and `psycopg`.
- `config/settings.py` loads the root `.env` using `python-dotenv` and requires
  `SECRET_KEY` and `DATABASE_URL`. Keep secret values out of documentation/output.
- No separate frontend build, REST API, Supabase SDK, or Supabase Auth integration
  is implemented in the current repository.
- Development settings currently use `DEBUG=True`, `ALLOWED_HOSTS=[]`, and UTC.

## Where things live

| Path | Responsibility |
| --- | --- |
| `manage.py` | Django command entry point |
| `config/` | Settings, root URLs, ASGI and WSGI entry points |
| `apps/register/` | Registration and all core clinic/ERD models |
| `apps/login/` | Session-based login |
| `apps/home/` | Dashboard and account-page integration tests |
| `apps/profile/` | Optional profile details and their form |
| `apps/user_settings/` | Saved account preference flags |
| `apps/joins/` | SQL JOIN learning page using fictional clinic records |
| `templates/<app>/` | Page templates |
| `templates/includes/navigation.html` | Shared authenticated navigation |
| `static/css/<app>/`, `static/js/<app>/` | Page styles and scripts |

The UI uses dark blue-green (`#19343d`), teal (`#117c77`), pale backgrounds,
Georgia headings, and Arial labels. Registration CSS imports login CSS;
settings CSS imports profile CSS. Most existing CSS is compressed onto one line.

## Routes and current flows

| URL | Name | Behavior |
| --- | --- | --- |
| `/register/` | `register:register` | Public patient registration |
| `/login/` | `login:login` | Public University ID/password login |
| `/` | `home:home` | Authenticated dashboard |
| `/dashboard/` | `home:dashboard` | Alias for the same dashboard view |
| `/profile/` | `profile:profile` | Authenticated profile form |
| `/settings/` | `user_settings:settings` | Authenticated settings form |
| `/joins/` | `joins:demo` | Authenticated INNER/LEFT JOIN activity |
| `/logout/` | `logout` | Django LogoutView, redirects to login |
| `/admin/` | Django admin namespace | Django admin entry point |

Registration saves an active `User` with type `Patient` and a linked `Patient`
record, then redirects to login. It collects University ID, first/last names,
email, emergency contact, medical history summary, and matching passwords.
The form explicitly checks duplicate school IDs and password confirmation.

Login calls Django `authenticate()` and `login()` and redirects to the root
dashboard. It currently always redirects to the dashboard rather than consuming
the `next` parameter. Already-authenticated users visiting login or registration
are also redirected to the dashboard.

Profile and settings views use `get_or_create(user=request.user)`, bind forms
on POST, save valid submissions, and redirect back to the same page. These
records are created lazily on the first visit rather than during registration.
Profile fields are `full_name`, `age`, `home_address`, and `bio`. Profile name
edits do not update the account's `fname`/`lname`; the dashboard greets by `fname`
with `school_id` as fallback.

Settings persist `dark_mode` and `email_notifications`. Theme switching and
notification delivery are not implemented. The dashboard currently provides a
greeting, navigation, and profile/settings cards, without appointment statistics.

## Custom user and data relationships

`AUTH_USER_MODEL = 'register.User'`. This user inherits from `models.Model`,
not `AbstractUser` or `AbstractBaseUser`. Authentication support is implemented
manually with `UserManager`, `set_password`, `check_password`, `get_username`,
and authentication/activity/staff properties.

- Primary key: `user_id`; login identifier: unique `school_id`.
- Names: `fname` and `lname`; email is unique.
- Password hashes are stored in `password_hash` using Django hashers.
- Roles: `Admin`, `Patient`, `Provider`.
- Statuses: `Active`, `Suspended`; `is_active` is based on this status.
- `is_staff` is based on the `Admin` role. Standard Django user permission/full
  name/session-hash APIs are not all present; inspect compatibility when working
  on auth or admin. Avoid assuming `username`, `password`, or `get_full_name()`.
- New cross-app user relations should use `settings.AUTH_USER_MODEL`;
  runtime user-model lookup can use `get_user_model()`.

Core models are all in `apps/register/models.py`, despite that app's name:

| Model | Table | Relationships / purpose |
| --- | --- | --- |
| `User` | `user` | Core account |
| `Admin` | `admin` | One-to-one account; access level and department |
| `Patient` | `patient` | One-to-one account; emergency contact, history, no-show count |
| `Provider` | `provider` | One-to-one account; specialization, room, activity flag |
| `Slot` | `slot` | Provider availability with start/end times and booking flag |
| `Appointment` | `appointment` | Patient, provider, and a one-to-one slot |
| `MedicalRecord` | `medical_record` | One-to-one appointment plus patient and provider |
| `SupportTicket` | `support_ticket` | User request assigned to an admin |
| `AuditLog` | `audit_log` | Admin action and target-record metadata |

`Admin`, `Patient`, and `Provider` use their user relation as their primary key.
Clinic models declare explicit ERD table/column names. Existing relationships
use cascading deletion. Preserve these schema choices unless a requested change
requires a migration.

`Profile` and `UserSettings` have one-to-one user relations named
`clinic_profile` and `clinic_settings`. Their default Django table names are
`profile_profile` and `user_settings_usersettings`. These account details are
separate from the role-specific `patient_profile`, `provider_profile`, and
`admin_profile` relations.

Appointment booking, provider scheduling, medical-record management, support
ticket handling, audit logging, and separate role dashboards currently exist
only as schema foundations. There are no application views/forms/templates
implementing those clinic workflows. Only Profile and UserSettings are registered
with Django admin; the custom user and clinic models are not registered.

## Migrations and checks

- `register/0001_initial` defines the nine core clinic models.
- `profile/0001_initial` creates the profile;
  `profile/0002_profile_age_profile_home_address` adds age and address.
- `user_settings/0001_initial` creates the preference record.
- Profile/settings initial migrations already depend on the configured user
  model. The dashboard fix corrected model references without changing schema.
- These profile/settings migrations were applied to the configured database
  during this conversation. Inspect migration state again before future work.

The original account suite has 12 tests: two login tests, two registration tests,
and eight account-page tests. Account tests cover login requirements, page rendering
and navigation, dashboard cards, profile/settings persistence, user isolation,
invalid age, unchecked settings, and labels for the custom user.
The suite passed using an isolated in-memory SQLite database on 2026-10-12;
that does not establish PostgreSQL-specific behavior or browser visual layout.

For Windows PowerShell, use the existing interpreter directly when activation
is unnecessary:

```powershell
.\venv\Scripts\python.exe manage.py runserver
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

For isolated tests, override `DATABASE_URL` in a disposable shell/tool process
so tests do not require creating a test database on the hosted PostgreSQL server:

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'
.\venv\Scripts\python.exe manage.py test
```

The override lasts for that shell process. Use a fresh terminal afterward for
running the application against its configured database. Keep model changes and
their Django migrations together. Check existing local changes before editing;
the user may have work that is not yet committed.

## SQL JOIN activity added on 2026-10-12

The instructor's activity is adapted to existing models; no additional schema
or project dependencies are required. `apps/joins/queries.py` uses parameterized
raw SQL for Patient INNER JOIN Appointment and Patient LEFT JOIN Appointment,
with a required User join for names. The demonstration filters to three reserved
school IDs AND fictional emails and does not show unrelated clinic records.

`python manage.py seed_join_demo` adds/reuses 3 fictional patients, 1 provider,
3 slots, and 3 appointments. It uses `JOIN-DEMO-001` through `JOIN-DEMO-004`,
fake `@join-demo.example.invalid` emails, suspended accounts, and unusable
passwords. It does not delete or overwrite existing records and uses a
transaction to roll back conflicts. These samples were added to the configured
Supabase database during this activity. Database primary keys are not fixed.

`python manage.py verify_join_demo` is read-only and prints SQL, parameters,
results, and checks. Ana has 2 appointments, Ben 1, Carlo 0: INNER yields 3
rows and LEFT yields 4, with Carlo's appointment columns NULL. Visiting `/joins/`
executes only SELECTs, and SQL joins is linked in the shared navigation.

Review `docs/sql_joins_activity.md`, `docs/sql_joins_examples.sql`, and
`docs/sql_joins_verification.md` for the activity mapping, all seven JOIN
definitions, sample SQL, and verification evidence. Activity tests are in
`apps/joins/tests.py`. The user has now requested the video plan/script;
`docs/sql_joins_video_script.md` contains spoken lines and screen cues.
Recording, sharing, and submission remain for the user. Browser visual QA remains for the user because
no browser surface was available; HTTP checks and PostgreSQL execution succeeded.
