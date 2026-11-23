# Step 8 reception, check-in and walk-in encounters

Implemented November 23, 2026. Visual review is pending.

## Verify locally

```powershell
Set-Alias -Name python -Value (Resolve-Path '.\tmp\venv-step5\Scripts\python.exe').Path -Scope Local
$env:TEKNOCARE_LOCAL_DB_PATH = 'tmp\step5-preview.sqlite3'
python scripts\check_project.py
python manage.py migrate --check --settings=config.settings_local
python manage.py collectstatic --noinput --dry-run --verbosity 0 --settings=config.settings_local
```

Open `http://127.0.0.1:8010/reception/`. If needed, start the preview with
`python manage.py runserver 127.0.0.1:8010 --settings=config.settings_local`.
The local preview has `clinical.0004_allow_blank_draft_complaint` applied.
This state-only migration allows an empty complaint at Draft intake and leaves
the underlying column and existing data in place. On a fresh local checkout,
run `python manage.py migrate --settings=config.settings_local` first.

## Manual browser review

1. **Queue and check-in.** Sign in as `DEMO-ADMIN`. Open **Reception queue**
   from the dashboard, then view a same-day fictional Scheduled appointment.
   Click **Check in patient**. Expect a **Checked in** badge and an
   **Open Draft encounter** form.
2. **Scheduled intake.** Choose an eligible attending provider and open the
   encounter. Expect a **Draft** badge, the student's captured affiliation,
   and separate scheduled and attending provider labels. Returning to the
   appointment shows **View linked encounter**. The Draft appears on the
   **Draft encounters** tab. Check the assignment form with a second active
   fictional practitioner if one is available.
3. **Walk-in.** From the Admin queue choose **Start walk-in**, enter an exact
   fictional patient University ID, continue, choose an attending provider
   and submit. Expect **Walk-in** and **Draft** on the encounter page. A
   second attempt for that patient's open walk-in shows a validation error.
4. **Status and scope.** A Scheduled slot can be marked **No show** after its
   end. A Checked in appointment can be marked **Completed** once its linked
   encounter is Finalized. The test suite supplies both cases. As a student,
   opening `/reception/` returns 403. As an eligible practitioner, verify the
   appropriate queue and that the Admin walk-in control is absent.
5. **Layout.** Check the dashboard, both queue tabs, appointment details,
   walk-in lookup and intake, and encounter assignment at desktop and narrow
   widths. Check both themes. Expect usable actions and scrollable wide tables.

## PostgreSQL verification

SQLite reported 179 passes and six PostgreSQL-only skips. System,
migration-drift, ERD, populated legacy upgrade and static dry-run checks passed.
All 108 selected tests passed on disposable PostgreSQL, including simultaneous
requests to open one scheduled encounter. The live preview redirected anonymous
reception requests to sign-in.

```powershell
python tmp\step6_postgres_check.py apps.appointments apps.clinical apps.common apps.home apps.providers apps.university
```

Hosted backup and populated database rehearsal are separate checkpoints.

## Commit and push after review

When the Git index still contains Step 7, commit and push that staged change
first. The Step 8 changes start in the working tree.

```powershell
git --no-pager diff --cached --name-status
git commit -m "feat: add patient booking cancellation and appointment history"
git push origin main
```

Then stage, review, commit and push Step 8.

```powershell
git status --short --branch
git --no-pager diff
git add -- README.md apps/appointments/services.py apps/clinical/forms.py apps/clinical/migrations/0004_allow_blank_draft_complaint.py apps/clinical/models.py apps/clinical/reception.py apps/clinical/reception_urls.py apps/clinical/reception_views.py apps/clinical/test_reception.py apps/common/permissions.py config/urls.py docs/access_policy.md docs/development_plan.md docs/step_8_verification.md templates/clinical/reception_appointment.html templates/clinical/reception_encounter.html templates/clinical/reception_queue.html templates/clinical/reception_walkin.html templates/home/home.html
git diff --cached --check
git --no-pager diff --cached
git commit -m "feat: add check-in walk-in intake and encounter assignment"
git push origin main
```
