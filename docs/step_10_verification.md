# Step 10 medication catalog and prescriptions

Run from the repository folder with your venv active. Stop the existing local
server first if it uses the same port.

```powershell
python scripts\check_project.py
python manage.py migrate --settings=config.settings_local
python manage.py runserver --settings=config.settings_local
```

Expect `prescriptions.0002_protect_prescription_history` to report `OK`, or
`No migrations to apply` if it is already applied. The migration adds guards
without changing the ERD or rewriting existing data.

The isolated check runner passed with 197 tests and seven PostgreSQL-only
skips. ERD agreement, the populated upgrade, and a local HTTP walkthrough
of draft, issue, patient print, and cancellation passed. PostgreSQL trigger
and concurrency verification remain pending on a disposable database.

## Three main checks

1. **Clinic Admin.** In **Clinic setup → Medication catalog**, add a fictional
   medication with code `DEMO-RX`, name `Fictional medication`, strength
   `Demo strength` and dosage form `Demo form`. Keep it active for the next
   check. If there is no Draft encounter for testing, open one for a fictional
   Patient through **Reception queue → Start walk-in** and assign an active
   Physician or Dentist. Once a prescription item references the medication,
   a change to its strength should be rejected, and an activity toggle should
   still save.
2. **Assigned Physician or Dentist.** Open **Clinical encounters → Draft →
   Prescriptions for this encounter** and start a draft. Try issuing it empty
   and expect a validation error. Add an item with fictional text for dose,
   route, frequency and quantity unit, and positive numeric values for duration
   and quantity. Issue it and confirm the item becomes read-only. A consultation
   with otherwise complete notes can finalize once all its drafts are issued
   or discarded. To check a correction, cancel the issued copy and open a
   replacement from the canceled copy. Use an assigned Draft encounter for
   the same patient. If the original encounter is Finalized, prepare a new
   Draft encounter first. The original dose and issue time should still display.
3. **Patient from the test encounter.** Open **Dashboard → My prescriptions**.
   Confirm the issued copy is visible and opens a print view with the prototype
   label and the original items. A canceled issued copy should remain visible
   with a **CANCELED** label. A replacement appears only once issued. Use
   **Ctrl+P** to check the print layout. As a second **Patient**, open the first
   patient's print URL directly and expect 404.

## Commit after review

```powershell
git status --short
git add .
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "feat: add authorized prescription drafting issuing and printing"
git push origin main
```

Review the working tree before using `git add .` so the commit contains only
the Step 10 changes.
