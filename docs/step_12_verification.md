# Step 12 student tuition charges

Stop the local server. With your venv already active, run these commands
from the folder containing `manage.py`.

```powershell
python manage.py migrate --settings=config.settings_local
python manage.py runserver --settings=config.settings_local
```

Expect `billing.0003_protect_original_charge_lines` to report `OK` or
`No migrations to apply`. It adds database history guards without changing
the ERD columns or rewriting charge records. Use a fictional Student with a
Finalized encounter, a fictional Faculty or Staff encounter, and an open
academic term. You can create an open term in **Clinic setup → Academic terms**.

## Three main checks

1. **Clinic Admin.** Open **Clinic setup → Tuition charges → Find an encounter**.
   Search by the Student's University ID, open the Finalized encounter, and
   create a PHP 100.00 charge. On **Tuition charges**, filter by term and
   **Pending**, then select **Export pending CSV**. Confirm the file has the
   charge code, student ID, term, description, amount and currency. Reload the
   detail and confirm it is still **Pending**. A Faculty or Staff encounter
   should instead show that the visit is free.
2. **Same Clinic Admin.** Open the Student charge, tick confirmation, and
   record the simulated posting. Check for **Posted** and a `DEMO-POST-`
   reference. Enter a fictional administrative reason, tick reversal
   confirmation, and record the simulated reversal. Expect **Voided**, the
   original posting reference, and a separate `DEMO-REV-` reference.
3. **Student Patient from the charge, then a different Patient.** Open
   **Dashboard → My tuition charges** and view the charge. Confirm the amount
   and **Voided** status with no action buttons. Copy the patient detail URL.
   Sign in as a different Patient and open that URL. Expect 404.

The CSV uses quoted fields and neutralizes formula-like text.
[OWASP CSV Injection](https://community.owasp.org/attacks/CSV_Injection)

## Commit after review

```powershell
git status --short
git add .
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "feat: add simulated tuition charge posting and reconciliation"
git push origin main
```

Check that the working tree contains only the Step 12 changes before staging.
The existing **Clinic checks** workflow runs the tests on disposable PostgreSQL
after a push. Applying this migration to hosted Supabase remains a separate step.
