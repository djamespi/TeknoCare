# Step 11 referrals and patient visit summaries

From the repository folder with your venv active, stop the local server and run:

```powershell
python scripts\check_project.py
python manage.py migrate --settings=config.settings_local
python manage.py runserver --settings=config.settings_local
```

Expect `clinical.0006_protect_referral_lifecycle` to report `OK` or
`No migrations to apply`. The migration adds history guards and leaves
existing records and ERD fields in place. Use fictional accounts and visits.
PostgreSQL verification remains pending on a disposable database.

The isolated checks passed with 205 tests and seven PostgreSQL-only skips.
ERD agreement and the populated legacy upgrade passed. A local HTTP
walkthrough covered referral authoring, Draft privacy, finalized summaries,
follow-up and the print stylesheet.

## Three main checks

1. **Assigned Physician or Dentist.** In **Clinical encounters → Draft →
   Referrals for this encounter**, add a fictional destination and
   patient-facing instructions. Expect a **Pending** referral with your name.
   Finalize the encounter after saving the required consultation fields and
   resolving any prescription drafts. The encounter should move to **Finalized**.
2. **Patient from that encounter.** Open **Dashboard → My visit summaries**.
   Open the finalized visit and confirm the referral and any current issued
   prescription appear. The summary excludes Draft encounters and internal
   consultation notes. Open **Print visit summary** and **Print referral** and
   check the prototype labels and print preview with **Ctrl+P**. Sign in as a
   second **Patient** and open the first patient's summary or print URL to
   verify it returns 404.
3. **Same assigned Physician or Dentist.** Open the Finalized visit's referral
   list and mark the Pending referral **Completed** or **Canceled**. Confirm the
   status changes and the original destination, wording, author and date remain.
   The referral should have no further follow-up action. The patient can reload
   their summary to see the updated status.

## Commit after review

```powershell
git status --short
git add .
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "feat: add referrals and patient visit summaries"
git push origin main
```

Review the working tree before using `git add .` so the commit contains only
the Step 11 changes.
