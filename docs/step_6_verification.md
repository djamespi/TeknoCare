# Step 6 provider and room availability

Implemented November 23, 2026. Visual review is pending.

## Verify locally

From the repository folder on the lab workstation, use the existing Python 3.12
environment and SQLite preview database.

```powershell
Set-Alias -Name python -Value (Resolve-Path '.\tmp\venv-step5\Scripts\python.exe').Path -Scope Local
$env:TEKNOCARE_LOCAL_DB_PATH = 'tmp\step5-preview.sqlite3'
python scripts\check_project.py
python manage.py collectstatic --noinput --dry-run --verbosity 0 --settings=config.settings_local
```

Open the running preview at `http://127.0.0.1:8010/`. If it is stopped, run
`python manage.py runserver 127.0.0.1:8010 --settings=config.settings_local`.
Step 6 uses the existing schema.

## Manual browser review

1. **Admin entry points.** Sign in as `DEMO-ADMIN` and open **Clinic
   availability** from the dashboard or Clinic setup. Expect a date range and
   provider filter, an **Add slot** button and a list of clinic slots.
2. **Add and filter.** With an active fictional provider and room, add a future
   slot, for example November 24 from 9:00 to 9:30 AM. Expect an **Available**
   entry at the entered Manila time. Filter for its start date and provider.
   Select another date to verify the result disappears. Choose a reversed date
   range to see a field error.
3. **Conflicts and edits.** Try a second open slot for the same provider from
   9:15 to 9:45 AM. Expect an overlap error. Try an adjacent slot starting at
   9:30 AM. Expect success. Open an unbooked slot, clear **Open for booking**
   and save. It should show **Inactive**. Reopen it while the resources are
   active. A past start or end at/before the start should give a field error.
4. **Protected booking.** With a fictional future slot still open and a
   fictional Student login, use Django's local shell to make one test booking.
   Use the slot ID from its **View slot** URL.

   ```powershell
   python manage.py shell --settings=config.settings_local
   ```

   ```python
   from apps.appointments.services import book_appointment
   from apps.patients.models import Patient
   slot_id = int(input("Fictional slot ID: "))
   student_id = input("Fictional student University ID: ").strip()
   patient = Patient.objects.get(patient__school_id=student_id, affiliation="Student")
   booking = book_appointment(actor=patient.patient, patient_id=patient.pk, slot_id=slot_id, reason_for_visit="Fictional availability review")
   exit()
   ```

   Reload the slot in the browser. Expect **Slot details**, a **Booking
   protected** badge, and the saved details. The slot has no edit form.
5. **Provider and Patient scope.** Sign in as the active provider and open
   **Your availability**. Expect their own slots and an Add slot form that uses
   their own provider automatically. Another provider's slot URL returns 404.
   The Student account receives 403 when opening `/availability/`.
6. **Layout.** Check the Admin and Provider dashboards, Clinic setup, and the
   availability list, add, edit and read-only views at desktop and narrow widths
   in both themes. Expect usable filters, readable dates and errors, and a
   horizontally scrollable table where needed.

## Automated results

The SQLite project runner discovered 163 tests. It reported 160 passes and
three PostgreSQL-only skips. ERD agreement, populated legacy upgrade and static
dry-run checks passed. All 56 selected tests passed on disposable PostgreSQL
16.16, including the independent room/provider exclusion checks and a
simultaneous room allocation test. On the lab workstation, repeat the
PostgreSQL appointment, permission, provider and reference-data checks with the
prepared local runner:

```powershell
python tmp\step6_postgres_check.py apps.appointments apps.common apps.providers apps.university
```

Hosted backup, populated PostgreSQL upgrade rehearsal and deployment are separate
checkpoints.

## Commit and push after review

```powershell
git status --short --branch
git --no-pager diff
git add -- README.md apps/appointments/availability_urls.py apps/appointments/availability_views.py apps/appointments/forms.py apps/appointments/models.py apps/appointments/services.py apps/appointments/test_availability.py apps/common/permissions.py apps/providers/eligibility.py config/urls.py docs/access_policy.md docs/development_plan.md docs/step_6_verification.md templates/appointments/slot_form.html templates/appointments/slot_list.html templates/appointments/slot_status.html templates/home/home.html templates/includes/management_list.html templates/university/management.html
git diff --cached --check
git --no-pager diff --cached
git commit -m "feat: manage provider and room availability"
git push origin main
```
