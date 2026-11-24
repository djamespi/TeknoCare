# Step 13 audit history and operational reports

With the venv active, restart the local server from the folder containing
`manage.py`. Step 13 uses the existing tables and adds no migrations.

```powershell
python manage.py runserver --settings=config.settings_local
```

## Three main checks

1. **Assigned Physician or Dentist, then Clinic Admin.** Open a fictional
   patient's encounter in **Clinical encounters**. Note its encounter ID.
   As Admin, open **Clinic setup → Audit history** and filter by the provider's
   University ID, action **Clinical encounter viewed**, and target table
   `medical_record`. Confirm the actor, timestamp and target ID match. The
   audit row contains no clinical notes or editing controls.
2. **Clinic Admin.** Open **Clinic setup → Operational reports**. Pick the
   date of a known fictional appointment or encounter and compare the status
   counts and provider workload with the source case. Pick the academic term
   from Step 12 and compare its Pending, Posted and Voided amounts with
   **Tuition charges** using the charges' creation dates. Clear the dates to
   compare the full term. At a narrow window width, check that the report
   cards stack and both tables can scroll horizontally.
3. **Patient, then Provider (Physician or Dentist).** Open
   `/clinic/audit/` and `/clinic/reports/` directly. Expect **403** on both
   pages for both roles. Use a Provider account with its own login and
   active provider profile.

Reports use inclusive Manila dates and show the current status of each source
row. Workload counts visits by attending provider. A term filter applies to the
tuition totals only. Known SQL JOIN assessment fixtures are excluded from
reports by exact University ID and email pairs.

## Commit after review

```powershell
git status --short
git add .
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "feat: add clinic audit review and operational reports"
git push origin main
```

Review the working tree before staging so the commit contains only Step 13.
