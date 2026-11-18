# Step 2: account security and access foundation

Implemented November 18, 2026, after the user pushed Step 0. No commit, push,
Computer Use or screenshot capture is performed by the agent. Visual approval
remains pending until the user checks the running pages and confirms in chat.

## Changes and boundaries

- Validated, atomic Student/personnel/provider provisioning, required-profile
  authentication checks, identity normalization and normalized unique indexes.
- Server-side role/ownership/clinical action policies; appointment/billing services
  enforce authorized actors rather than trusting caller-supplied ownership/role.
- Password-change and Admin-assisted non-Admin reset pages, safe login redirects,
  suspension/session rules and read-only Django admin with no password hashes.
- Existing login/registration/navigation pages updated. Profile/preferences GETs
  no longer create rows. The SQL JOIN demo remains absent.
- [Access policy and limits](access_policy.md) distinguish current services from
  later clinic screens. Reference/account-management UI is Step 4; clinical,
  appointment and billing screens stay in their planned later steps.
- Migration `register.0004_normalized_identity_uniqueness` changes indexes only;
  the 22 entities/28 FKs, columns, original migrations and legacy archives remain.
  Configured Supabase and the user's existing local database are not migrated by
  the agent. Apply the local migration yourself before checking the pages.

## Automated verification

Agent result: the full isolated check runner passes with **88 tests passed and
one PostgreSQL-only test skipped** (89 discovered). Migration drift, ERD metadata
and populated legacy upgrade checks pass. The local HTTP smoke check passes.
`git diff --check` passes; Git's existing LF/CRLF notices are informational.

From the project folder with the venv active:

```powershell
python scripts\check_project.py
```

Expected: dependency consistency, system checks, no migration drift, feature/security
tests, all 22 ERD entities/28 relationships and populated legacy upgrade pass.
One PostgreSQL-only exclusion test is skipped on SQLite. Expected final line:
**All isolated project checks passed. Supabase was not used.**

The security tests cover normalized duplicates including bulk writes, ambiguous
legacy migration rejection without rewriting data, atomic provisioning rollback,
crafted role fields, required subtype failures, stale/suspended actors, owning vs
unrelated patients, active/inactive/unverified provider designations, nurse triage,
Admin-as-provider/self-treatment, booking state, CSRF/method guards, safe redirects,
password validation, reset reauthentication, session revocation and read-only admin.
Synchronous and async backend paths use the same custom-user access rules.

A real local HTTP smoke check uses a separate ignored fictional SQLite database,
normal local password hashing and standard-library HTTP requests. It checks login,
safe return to Profile, password changes, old-session rejection, Admin reset,
forbidden access, static CSS, read-only admin and the intentional `/joins/` 404.
This is not a visual review or browser UI automation. PostgreSQL CI, hosted
migration, concurrency/backup rehearsal and user visual approval are not claimed.

## Start and manually confirm

Stop the older server with **Ctrl+C**, then run:

```powershell
python manage.py migrate --plan --settings=config.settings_local
python manage.py migrate --settings=config.settings_local
python manage.py bootstrap_local_demo --settings=config.settings_local
python manage.py runserver --settings=config.settings_local
```

Expected: `register.0004_normalized_identity_uniqueness` applies with `OK` (or no
pending migrations on repeat). Bootstrap reuses your existing `DEMO-ADMIN` password;
if the account is new it prompts privately. If migration reports duplicate normalized
IDs/emails, stop and share the error text, not private records. Do not delete/merge
accounts, fake migrations or switch to Supabase to bypass the failure.

1. **Student registration:** Open `http://127.0.0.1:8000/register/`. Use fictional
   details, an unused ID such as `001-Step2`, and `step2@example.invalid`. Try a
   weak password first: expect an inline error and no registration. Then use a
   strong password you choose privately: expect sign-in with a success message.
   Repeat that email with another ID/capitalization: expect a duplicate error.
2. **Login/navigation:** Sign in with the exact ID case and chosen password.
   Expect Dashboard, Profile, Settings, Change password and Sign out. A Student
   must not see Reset account password. Profile/Settings must still save only
   their own details. An incorrect ID/password shows a form error, not a server
   traceback. `/joins/` remains 404.
3. **Own password:** Sign in as that Student in a second independent browser or
   private window. In the first, open Change password. Try a wrong current
   password and a weak/mismatched new password: expect field errors, no change.
   Set a valid replacement: expect a success notice and the first window stays
   signed in. Refresh Dashboard in the second window: expect sign-in. The old
   password must fail and the replacement must succeed.
4. **Admin reset:** Sign in as `DEMO-ADMIN`. Open Reset account password. Wrong
   Admin password must fail without changing the Student. Reset the fictional
   Student using your correct Admin password and a strong replacement: expect
   success, no email, and Student sessions must sign in again. Verify the new
   password works. Targeting `DEMO-ADMIN` instead must be forbidden (403).
   A signed-in Student opening `/login/reset-password/` directly must also get 403.
5. **Read-only Django admin:** As `DEMO-ADMIN`, open `/admin/`, then Users and the
   fictional Student's details. Expect read-only fields, no Save/Add/Delete
   controls and no password/hash field. `/admin/register/user/add/` must give 403.
   A Student opening `/admin/` must be denied/redirected to admin sign-in.
6. **Visual confirmation:** Check login, registration and both password pages on
   desktop and a narrow window. Labels, field errors, status notices and wrapped
   navigation must remain readable; buttons must work without overlapping.
   Sign out returns to login. Confirm the results in chat; no screenshots needed.

Suspension, personnel provisioning and provider-policy cases are automated tests
for service APIs here, not yet manual Admin screens. Do not enter real clinical
data, publish test credentials or assume university identity has been verified.

## Review, commit and push after approval

From `C:\Users\ADMIN\CITU_TeknoCare\TeknoCare`, branch `main`, remote `origin`:

```powershell
git status --short
git --no-pager diff
git add .
git diff --cached --check
git --no-pager diff --cached --stat
git commit -m "feat: enforce account provisioning and clinic access policies"
git push origin main
```

`git add .` is appropriate only after reviewing that all changed/untracked files
belong to this step. Inspect new files in your editor, or use
`git --no-pager diff --cached` for the complete staged patch. Never stage `.env`,
passwords, venv, databases or unrelated work. If checks or manual actions fail,
stop before committing and share the action/error text for correction.
