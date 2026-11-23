# Step 5 patient details, intake, and allergies

Implemented November 23, 2026 after the user confirmed Step 4 visual approval.
Step 5 manual visual review is pending.

## Local verification

On the November 23 lab workstation, point `python` at the Step 5 environment for
this PowerShell session and select the prepared SQLite preview database. The
original `venv` uses Django 4.2, and the alias works without an activation script.

```powershell
Set-Alias -Name python -Value (Resolve-Path '.\tmp\venv-step5\Scripts\python.exe').Path -Scope Local
$env:TEKNOCARE_LOCAL_DB_PATH = 'tmp\step5-preview.sqlite3'
```

From the repository folder, run:

```powershell
python --version
python -m django --version
python scripts\check_project.py
python manage.py collectstatic --noinput --dry-run --verbosity 0 --settings=config.settings_local
python manage.py bootstrap_local_demo --settings=config.settings_local
python manage.py runserver 127.0.0.1:8010 --settings=config.settings_local
```

Expect Python 3.12 and Django 5.2.19. The lab preview database already has the
project migrations. On another machine with a fresh local database, run
`python manage.py migrate --settings=config.settings_local` before bootstrapping.
Use fictional accounts and details. Open `http://127.0.0.1:8010/` for the review.
On the lab workstation, another local service uses port 8000. If the preview is
already running on 8010, open it directly.

Automated results on Django 5.2.19: 150 tests passed and one PostgreSQL-only
test skipped. Dependency, system, migration-drift, ERD, populated legacy upgrade
and static dry-run checks passed. The local HTTP smoke test verified login,
registration, sign-in redirects for Step 5 pages and shared CSS delivery.

## Manual browser review

1. **Admin intake.** Sign in as `DEMO-ADMIN` and open **Patient intake** at
   `/clinic/patients/`. Create a Student login with University ID
   `DEMO-STEP5-STUDENT`, then create a Faculty or Staff login. Confirm the
   affiliation on each form. Search by ID or name and filter by affiliation.
   Expect the matching rows and the Patient account role.
2. **Existing login and corrections.** Choose **Add a patient profile to an
   existing account** and search for the exact `DEMO-ADMIN` ID. Attach a Staff
   Patient profile if the account has none. Expect the Admin workspace and a new
   **Patient details** link. Use **Identity** or **Affiliation** on a fictional
   intake row to review or correct its details. A known affiliation cannot be
   cleared. An ID correction changes the University ID used at sign-in. Keep
   `DEMO-STEP5-STUDENT` unchanged if using the allergy fixture below.
3. **Patient details.** Sign in as the Student. Open **Patient details** from the
   dashboard or Profile. Save a past birth date and check the derived age. Try
   tomorrow's date and expect a validation error. Add two emergency contacts,
   select the second as primary, then edit the first to make it primary again.
   Expect just one Primary badge. Opening **Remove** shows a confirmation.
   Submitting that form removes only the selected contact. Opening
   `/clinic/patients/` as the Student returns 403.
4. **Allergy review.** As Admin, provision an active fictional Physician
   `DEMO-STEP5-CLINICIAN` through **Clinic setup → Providers**. In a second
   terminal create an assigned fictional Draft visit in the same local database.
   Encounter creation pages are scheduled for Step 8.

   ```powershell
   Set-Alias -Name python -Value (Resolve-Path '.\tmp\venv-step5\Scripts\python.exe').Path -Scope Local
   $env:TEKNOCARE_LOCAL_DB_PATH = 'tmp\step5-preview.sqlite3'
   python manage.py shell --settings=config.settings_local -c "from apps.clinical.models import MedicalRecord; from apps.patients.models import Patient; from apps.providers.models import Provider; patient = Patient.objects.get(patient__school_id='DEMO-STEP5-STUDENT'); provider = Provider.objects.get(provider__school_id='DEMO-STEP5-CLINICIAN', is_active=True); print(MedicalRecord.objects.get_or_create(patient=patient, provider=provider, status=MedicalRecord.Status.DRAFT, chief_complaint='Fictional Step 5 allergy review')[1])"
   ```

   With the Physician login, open **Allergy review**. An unrelated patient's
   exact ID produces the same result as an unknown ID. Search
   `DEMO-STEP5-STUDENT`, record a fictional allergen, and edit its severity.
   Sign in as the Student and verify the updated row appears on **Patient details**
   without editing controls. A newly created patient without allergy entries
   sees **Allergies are not documented**.
5. **Layout.** Check Dashboard, Profile, registration, Patient intake and its
   forms, Patient details, and Allergy review at desktop and narrow widths. Switch
   themes in Settings. Expect readable lists, horizontally scrollable wide
   tables, visible form errors and usable controls at both widths.

The test client covers ownership, scoped provider access, form validation and
audit writes. Manual layout review and PostgreSQL concurrency remain unverified.
Hosted Supabase is a separate checkpoint.

## Commit and push after review

```powershell
git status --short --branch
git --no-pager diff
git add -- README.md apps/common/permissions.py apps/patients/forms.py apps/patients/intake_urls.py apps/patients/intake_views.py apps/patients/services.py apps/patients/test_workflows.py apps/patients/urls.py apps/patients/views.py apps/profile/views.py apps/register/forms.py apps/register/services.py apps/register/tests.py config/urls.py docs/access_policy.md docs/development_plan.md docs/interface_patterns.md docs/step_4_verification.md docs/step_5_verification.md templates/home/home.html templates/includes/navigation.html templates/patients/account_lookup.html templates/patients/allergy_lookup.html templates/patients/allergy_table.html templates/patients/clinical_allergies.html templates/patients/contact_remove.html templates/patients/details.html templates/patients/form.html templates/patients/intake_list.html templates/profile/profile.html templates/register/personnel_list.html templates/university/management.html
git diff --cached --check
git --no-pager diff --cached
git commit -m "feat: add patient intake contacts and allergy management"
git push origin main
```
