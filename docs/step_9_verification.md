# Step 9 clinical documentation and finalization

The clinical worklist at `/clinical/` gives eligible practitioners access to
their assigned visits. A Nurse can also open Draft encounters for today's
Manila triage queue, view allergies and enter the measurements actually taken.
The assigned Physician or Dentist can save the chief complaint, symptoms,
examination notes, treatment plan and multiple catalog diagnoses, with at most
one primary diagnosis. Nonclinical Admins keep operational reception access
and can add entries to the diagnosis catalog through Clinic setup.

Finalization is a separate confirmation. The clinician must first save a
chief complaint, either symptoms or examination notes, and a treatment plan.
A diagnosis and vitals are optional. A linked Checked in appointment becomes
Completed in the same transaction. Draft changes, vitals and finalization
are audited, with the server recording the actor. Stale forms require a reload.

`clinical.0005_protect_finalized_clinical_details` installs SQLite and PostgreSQL
triggers without rewriting existing rows. The guards reject changes to
finalized vitals, diagnosis links and referral content, deletion of finalized
encounters, and changes to catalog entries while linked. The referral guard
allows status-only changes for a future authorized follow-up workflow. There
are no referral follow-up or amendment pages in this step.

## Before reviewing locally

From the repository folder with the venv active, stop the old development
server with **Ctrl+C** and run the following.

```powershell
python scripts\check_project.py
python manage.py migrate --settings=config.settings_local
python manage.py runserver --settings=config.settings_local
```

Expect the isolated checks to pass and the migration to report `OK` or
`No migrations to apply`. PostgreSQL-only tests are skipped in SQLite.
Use fictional data. If starting with an empty local database, run
`python manage.py bootstrap_local_demo --settings=config.settings_local`
after migrating to create or reuse the local Admin login.

Local verification passed with 189 tests and six PostgreSQL-only skips. The
ERD and populated legacy upgrade checks passed. A local HTTP smoke test
confirmed nurse vitals, draft notes with a primary diagnosis, read-only
finalized details and automatic completion of the linked appointment.

The configured Supabase project was observed to have the older schema during
the separate assignment. Its database upgrade requires the repository's
[migration checkpoint](supabase_migration_checklist.md). Step 9 verification
uses isolated SQLite. The PostgreSQL trigger path remains to be verified on a
disposable PostgreSQL database.

## Manual browser checks

1. As **DEMO-ADMIN**, open **Clinic setup → Diagnosis catalog**. Add two
   entries under a fictional system such as `Prototype` with codes `DEMO-A`
   and `DEMO-B`. Attempt the same code in the same system twice. Expect a form
   error on the duplicate.
2. Use your existing fictional Patient, active Physician or Dentist, and active
   Nurse accounts. If needed, provision and activate practitioners in
   **Clinic setup → Providers** and create a fictional Patient in **Patient
   intake**. Open **Reception queue → Start walk-in** as Admin, select the
   patient by exact University ID and assign the attending Physician or Dentist.
   Expect a Draft encounter with today's Manila time.
3. In another browser session, sign in as the **Nurse**. Open **Clinical
   encounters** and open today's Draft. Expect allergy alerts and a vitals
   section, without clinical notes, diagnosis controls or finalization.
   Submit the empty vitals form, then try entering only one BP value. Both
   attempts should fail. Enter a fictional pulse such as `75` and save.
   Expect a row with the Nurse's name and the server timestamp.
4. Sign in as the **attending Physician or Dentist**. The same encounter
   should show recorded vitals, allergy alerts and any in-scope prior visits.
   Try finalizing an empty Draft and expect required-documentation feedback.
   Save a fictional complaint, symptoms or examination notes, and a treatment
   plan. Select both demo diagnoses and pick one as Primary. Reload and verify
   that both are saved and the primary choice persists.
5. To check stale forms, open this Draft in two tabs. Save a note change in
   the first, then submit a different change from the second. Expect a reload
   message and preservation of the first change.
6. Reload the updated Draft, check the finalization confirmation and click
   **Finalize encounter**. The Finalized view should display the saved details
   and no write forms. Use the worklist's **Finalized** filter to reopen it.
   Repeat with a fictional Checked in appointment opened in reception.
   Expect the encounter status to become Finalized and the appointment status
   to become Completed together. A walk-in has no appointment status.
7. As nonclinical **Admin** or a **Patient**, open the clinical URL directly and
   expect denial. An unrelated eligible practitioner should receive 404 for
   that Draft. Check the forms and scrollable vitals table at a narrow width,
   in both display themes, and confirm the results in chat.

## Commit after review

```powershell
git status --short
git add .
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "feat: document consultations and protect finalized clinical history"
git push origin main
```

Review the working tree before using `git add .` so the commit contains only
the Step 9 changes.
