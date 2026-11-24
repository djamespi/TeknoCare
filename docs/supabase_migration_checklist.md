# Supabase migration checkpoint

The read-only connection checkpoint passed on November 25, 2026. Django
connected through the Supabase session pooler with TLS. The hosted schema
upgrade is still pending. Use the [local startup guide](../README.md) for
normal prototype work until the hosted schema is ready.

## Inventory before changing data

- Identify the intended Supabase project, database, PostgreSQL version and connection
  mode privately. Django 5.2 requires PostgreSQL 14 or newer. Keep URLs/passwords
  out of Git, screenshots, command history and reports.
- Use reviewed environment-backed settings, not local/test settings. Environment
  variables take precedence over `.env`; confirm the target privately before any
  connection. No test, seed or migration command runs against hosted data merely
  because its URL already exists in `.env`.
- At the requested read-only inventory checkpoint, set `DEBUG=false`, the intended
  hosts/secret and reviewed database connection. These commands read migration state
  and preview pending work without applying migrations:

  ```powershell
  $env:DEBUG = 'false'
  $env:DATABASE_SSL_REQUIRE = 'true'
  .\venv\Scripts\python.exe manage.py showmigrations --settings=config.settings
  .\venv\Scripts\python.exe manage.py migrate --plan --settings=config.settings
  ```

  An inherited non-boolean `DEBUG` value blocked settings startup during the
  inspection. The current-shell override resolves it without changing the
  saved credentials or other environment settings.

- Compare the actual schema to recorded Django migrations and the checked-in
  22-entity ERD. Earlier manually created tables are not proof migrations ran.
  Investigate missing/extra columns, provider mismatches and unverified legacy
  affiliation/rooms before proposing a fix; do not fabricate clinical values.
- Check extension/function/trigger permissions, source-table grants and RLS, and
  restricted access to `legacy_*` archives. Django object authorization does not
  replace database grants/RLS. No public exposure is needed for this prototype.
- Step 2 adds `register.0004_normalized_identity_uniqueness`. Inventory duplicates
  of SQL `TRIM(school_id)` and `LOWER(TRIM(email))` privately before the migration.
  Its preflight stops on collisions without rewriting identities. Resolve any
  collision through a reviewed reconciliation, not by deleting accounts, inventing
  IDs or faking migration records. Rehearse the expression indexes with the actual
  PostgreSQL collation and representative legacy whitespace/email values. Existing
  sessions need to sign in again after the authentication-backend change. Check
  required subtype presence and [Admin/access policy](access_policy.md) as well.

## Public table cleanup inventory

The configured database contains seven current ERD tables, seven Django
framework tables, and four tables from the original application schema.

| Original table | Role in the upgrade |
| --- | --- |
| `profile_profile` | Contains profile records. The migrations preserve them and move the live profile to `user_profile`. |
| `user_settings_usersettings` | Contains preferences. The migrations preserve them and move the live preferences to `user_settings`. |
| `admin` | Empty at inspection. The original `audit_log` still references it, so migrate the audit relationship before archiving it. |
| `support_ticket` | Empty at inspection. The migration archives it as `legacy_support_ticket` and retires the ticket model. |

The public schema contained no unrelated application tables. Keep Django's
migration, session, permissions, content type and admin log tables for
framework operations. The migrations retain protected legacy archives for
history and recovery.

## Backup and staging gate

1. Create a backup of the current application schema/data and required database
   objects, using a method available on the actual Supabase plan. Protect dumps
   outside Git. Record the backup time/location privately.
2. Restore the backup into isolated PostgreSQL staging; verify it really restores,
   including IDs, links, legacy archives and migration history. Use fictional or
   appropriately de-identified representative data for demonstrations/tests.
3. Rehearse pending migrations with the same code/dependency revision intended for
   hosting. Use a direct database connection for migration work, following
   [Supabase's connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres).
   If networking requires a session-pooler alternative, validate it in staging.
   Do not assume the transaction pooler has the same migration/session behavior.
4. Verify `btree_gist`, range exclusions and trigger installation. Test normal,
   invalid, direct/bulk and concurrent write cases against disposable PostgreSQL.
   SQLite and the GitHub baseline test job do not replace this rehearsal.
5. Verify account/profile keys, visit timestamps, structured patient/clinical
   relationships and every retired-field archive after the upgrade. The new profile
   replacement must be recognized as already satisfied if its original was applied.
   Preserve all original migration files and `BASELINE_COMMIT.txt`.
6. Record validation results and unresolved data issues. `register.0002` cannot be
   reversed through Django; rehearse recovery from the verified backup. Plan a
   write pause/compatible code deployment if the schema update needs one.

Consult the official [backup/restore guide](https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore)
for commands appropriate to the actual project. No backup, external restore,
privilege change or hosted migration is performed just by adding this runbook.

## Reviewed hosted upgrade and confirmation

Provide the student with the concrete target, pending migration list, verified
backup/restore result, staging evidence and expected effects. The project guide
requires a verified backup and PostgreSQL rehearsal before a hosted upgrade.
Only at the separately authorized checkpoint apply the reviewed migration plan,
deploy the compatible app revision, and check the applied state afterwards.

Do not run the automated test suite or demo seed on Supabase. Do not use `--fake`,
delete migration history, drop application tables or delete ambiguous records to
force a migration through. Git push does not apply database migrations.

Post-upgrade confirmation includes migration status, preserved row/link checks,
constraints/triggers, authorized fictional-account sign-in and the feature's
screens. Avoid editing real records to prove a screen works. Record the actual
outcome in `development_plan.md`; if an upgrade fails, stop writes and follow the
rehearsed recovery plan instead of guessing a reverse migration.

For the website persistence check, point Django's `config.settings` at the
reviewed staging PostgreSQL database. Register a fictional Student in the
website, sign in, and book an available slot. From a separate database
connection, verify that the new `user` links to a Student `patient` and the
matching `appointment` is Scheduled. Compare the appointment ID with the
website detail page.

## Current checkpoint record

| Check | Current evidence |
| --- | --- |
| Local fresh SQLite migration | Covered by local rehearsal and isolated tests |
| Populated legacy SQLite upgrade | Automated script, including replacement/already-applied recognition |
| ERD/model agreement | Automated metadata comparison for 22 entities / 28 relationships |
| Disposable PostgreSQL legacy rehearsal | PostgreSQL 16.16 physical backup and restore passed with fictional original-schema data. See [Step 14 evidence](step_14_verification.md#postgresql-rehearsal-evidence). |
| Current Supabase schema/version | PostgreSQL 17.6. Django migration history is consistent, with 22 recorded migrations, 26 pending migrations, and 7 of 22 current clinic tables present. |
| Legacy data preflight | Zero normalized University ID or email collisions, provider/slot mismatches, nonpositive slot durations, and incompatible appointment statuses at the read-only checkpoint. |
| Supabase-version schema and persistence rehearsal | All 26 migrations passed on disposable PostgreSQL 17.6 with fictional legacy data. Physical tables matched all 22 ERD entities and 28 foreign keys. HTTP signup, sign-in and booking passed, and a separate database connection confirmed persistence. |
| Hosted API access | Review of API grants, exposed schemas and RLS is required before serving clinic data. See [Supabase Data API security](https://supabase.com/docs/guides/api/securing-your-api). |
| Verified hosted backup/restore and staging rehearsal | Pending |
| Hosted upgrade authorization/application | Pending, following backup, staging and access review. |
