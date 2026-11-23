# Step 7 patient appointments and cancellation

Implemented November 23, 2026. Visual review is pending.

## Verify locally

On the lab workstation, use the prepared Python environment and SQLite preview.

```powershell
Set-Alias -Name python -Value (Resolve-Path '.\tmp\venv-step5\Scripts\python.exe').Path -Scope Local
$env:TEKNOCARE_LOCAL_DB_PATH = 'tmp\step5-preview.sqlite3'
python scripts\check_project.py
python manage.py collectstatic --noinput --dry-run --verbosity 0 --settings=config.settings_local
```

Open the preview at `http://127.0.0.1:8010/`. If stopped, run
`python manage.py runserver 127.0.0.1:8010 --settings=config.settings_local`.
Step 7 uses the existing schema.

## Manual browser review

1. **Browse.** Sign in with the fictional Student login. From the dashboard,
   open **My appointments → Book an appointment**. Expect a list of open future
   slots. Filter by Manila date, provider, then type. If choices are empty,
   add future open slots from **Clinic availability** as Admin first.
2. **Confirm a booking.** Select a time and enter a fictional reason. A blank
   reason shows a validation error. Submit a reason and expect **Appointment
   booked**, a **Scheduled** badge and the slot details. The appointment
   appears in **Upcoming** and its slot leaves the available times list.
3. **Reschedule.** Open that appointment, choose **Reschedule**, select a
   different time and review **Confirm new appointment time**. Submit and check
   the replacement is Scheduled. The original appears as Canceled in **History**.
   To exercise a stale request, open a replacement confirmation page, close
   that replacement from the Admin availability page in another session,
   then submit the old form. Expect an availability message and the original
   appointment to stay Scheduled.
4. **Cancel.** Open the new Scheduled appointment and choose **Cancel
   appointment**. **Keep appointment** returns without changing it. Confirm
   cancellation and expect a Canceled detail page and a History entry. While
   its provider and room stay eligible and the slot stays open, it reappears
   among the available times.
5. **Ownership.** In a second fictional patient login, open the first student's
   detail or cancellation URL. Expect 404. In each account, **My appointments**
   shows only that patient's history.
6. **Layout.** Check the available times, confirmations, upcoming and history
   tabs, and appointment details at desktop and narrow widths in both themes.
   Expect visible filter, error and action controls and horizontally scrollable
   tables where needed.

## Automated results

SQLite reported 172 passes and five PostgreSQL-only skips. System,
migration-drift, ERD, legacy-upgrade and static dry-run checks passed. All 94
selected tests passed on disposable PostgreSQL 16.16. The booking race tests
cover concurrent requests for the same slot and for overlapping slots for one
patient. The live preview served sign-in and redirected anonymous appointment
requests to sign-in.

```powershell
python tmp\step6_postgres_check.py apps.appointments apps.common apps.home apps.providers apps.university
```

The separate hosted backup and populated PostgreSQL rehearsal are still
pending. Reception and encounter actions are scheduled for Step 8.

## Commit and push after review

```powershell
git status --short --branch
git --no-pager diff
git add -- README.md apps/appointments/booking_urls.py apps/appointments/booking_views.py apps/appointments/forms.py apps/appointments/models.py apps/appointments/services.py apps/appointments/test_booking.py apps/common/permissions.py apps/home/test_interface.py config/urls.py docs/access_policy.md docs/development_plan.md docs/step_7_verification.md templates/appointments/booking_cancel.html templates/appointments/booking_detail.html templates/appointments/booking_form.html templates/appointments/booking_list.html templates/appointments/booking_slot_details.html templates/appointments/booking_slots.html templates/home/home.html
git diff --cached --check
git --no-pager diff --cached
git commit -m "feat: add patient booking cancellation and appointment history"
git push origin main
```
