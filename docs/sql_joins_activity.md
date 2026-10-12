# SQL JOIN activity adapted to TeknoCare

## Activity requirements and implementation

The supplied instructor guide requires research on seven JOIN types and a working
Django demonstration of at least two. Each selected JOIN needs correct SQL,
sample data, visible results, and an explanation of matching/unmatched rows.

This implementation reuses TeknoCare rather than creating the guide's separate
Student/Enrollment starter project. Its existing User, Patient, Provider, Slot,
and Appointment models already supply a relational schema and migrations.
No new models, tables, migrations, or project dependencies are needed.

| Requirement before recording | Where it is satisfied |
| --- | --- |
| Verify Python/Django | Existing venv: Python 3.12.10 and Django 4.2.30 |
| Explain all seven types | Comparison below |
| Choose at least two useful JOINs | INNER JOIN and LEFT JOIN on patients/appointments |
| Relational models and foreign keys | `apps/register/models.py` |
| Matching and unmatched sample records | `apps/joins/demo_data.py`, `seed_join_demo` command |
| Django query implementation | `apps/joins/queries.py`, called by `apps/joins/views.py` |
| Correct SQL shown | `/joins/` and `verify_join_demo`; standalone SQL below |
| Results in readable tables | `templates/joins/join_demo.html` |
| Inclusion, exclusion, repeated names, NULL explained | Web page and this guide |
| Actual behavior checked | `apps/joins/tests.py` and live verification |
| Recording plan and spoken script | `docs/sql_joins_video_script.md` |
| Recording, Drive upload, final submission | Student performs these after reviewing and practicing |

The PDF's example deletes all Student rows to reset its practice dataset. This
project's setup does not copy that reset: it only inserts missing fictional
records, reuses identical samples, and refuses conflicting records.

## SQL and relational foundations

SQL retrieves and changes table data; this activity uses SELECT statements.
A primary key identifies a row, and a foreign key points to another table's row.
A JOIN creates result rows by combining rows according to a condition. It does
not merge the underlying tables or insert new records.

For TeknoCare:

```text
User.user_id  <-- Patient.patient_id (one-to-one / patient's primary key)
Patient.patient_id <-- Appointment.patient_id (foreign key / one-to-many)
Provider.provider_id <-- Appointment.provider_id
Slot.slot_id <-- Appointment.slot_id (one-to-one)
```

The important condition for both selected examples is:

```sql
ON p.patient_id = a.patient_id
```

The patient ID must match the appointment's patient foreign key, not its
appointment ID, slot ID, school ID, or provider ID. The `"user"` table provides
names through `p.patient_id = u.user_id`. The raw table names come from
`Meta.db_table` in the existing models, not Django's usual app-prefixed defaults.

## Seven JOIN types and their fit here

| Type | Meaning | TeknoCare use / decision |
| --- | --- | --- |
| INNER | Matching pairs only | Appointment reports with patient/provider details. Selected. |
| LEFT | All left rows; NULL for missing right matches | All patients, even without appointments. Selected. |
| RIGHT | All right rows; NULL for missing left matches | Same preservation goal as reversing a LEFT JOIN. Unnecessary here. |
| FULL OUTER | Matches and unmatched rows from both sides | Reconciliation across independent datasets; limited benefit for this required foreign key. |
| CROSS | Every possible pair, N x M rows | Hypothetical patient/provider planning matrix, not actual bookings. |
| NATURAL | Matches every shared column name automatically | Prefer explicit ON conditions; new shared columns can change its meaning. |
| SELF | Same table in two aliased roles | Compare provider pairs with the same specialization; avoid duplicates with `p1.provider_id < p2.provider_id`. |

INNER and LEFT are selected because they answer clinic questions and clearly
contrast the treatment of a patient without appointments. Required appointment
foreign keys prevent orphan appointments under enforced constraints; do not
invent invalid records just to make RIGHT/FULL look different. SELF JOIN is a
pattern using aliases, rather than a literal `SELF JOIN` SQL keyword.

More useful future relationships include Provider LEFT JOIN Slot (providers
without availability), Appointment LEFT JOIN MedicalRecord (appointments without
records), User LEFT JOIN Profile (accounts without saved profiles), and
SupportTicket INNER JOIN User/Admin (requester and handler details). These are
project ideas, not additional implemented requirements in this activity.

## Fictional sample dataset

| School ID | Patient | Number of appointments |
| --- | --- | --- |
| JOIN-DEMO-001 | Ana Reyes | 2 |
| JOIN-DEMO-002 | Ben Santos | 1 |
| JOIN-DEMO-003 | Carlo Lim | 0 |

| Patient | Reason | Status |
| --- | --- | --- |
| Ana Reyes | Routine check-up | Scheduled |
| Ana Reyes | Follow-up consultation | Completed |
| Ben Santos | Health clearance | Scheduled |

A fictional provider, Maya Cruz (`JOIN-DEMO-004`), and three 30-minute booked
slots satisfy Appointment's required foreign keys. Slots start on 2026-10-13
at 09:00, 10:00, and 11:00 UTC. These are illustrative fixtures, not a functioning
scheduling/medical-record workflow. They use fake `@join-demo.example.invalid`
emails. All sample accounts are suspended, have unusable passwords, and cannot
sign in. Use your normal TeknoCare account to open the protected demonstration.

Database primary keys are assigned normally; existing rows are not overwritten.
Do not assume IDs equal 1, 2, and 3. The application filters by the sample school
IDs AND fake emails, so unrelated patient information is not displayed.

## Selected JOIN 1: INNER JOIN

Clinic question: which sample patients have appointments?

The implementation joins Patient to User for names and INNER JOINs Appointment
using the patient's ID. Every matching appointment creates a result row.

| Patient | Reason | Status |
| --- | --- | --- |
| Ana Reyes | Routine check-up | Scheduled |
| Ana Reyes | Follow-up consultation | Completed |
| Ben Santos | Health clearance | Scheduled |

Expected: three rows and two distinct patients. Ana's repeated name reflects
two different appointment IDs, not an accidental duplicate. Carlo has no matching
appointment and is excluded. DISTINCT is unnecessary for an appointment report.

## Selected JOIN 2: LEFT JOIN

Clinic question: what appointments does every sample patient have, including
patients with none?

The identity join to User is still INNER because that relation is mandatory.
Only the Patient-to-Appointment join changes to LEFT JOIN.

| Patient | Reason | Status |
| --- | --- | --- |
| Ana Reyes | Routine check-up | Scheduled |
| Ana Reyes | Follow-up consultation | Completed |
| Ben Santos | Health clearance | Scheduled |
| Carlo Lim | NULL | NULL |

Expected: four rows and three distinct patients. Carlo's patient ID/name exist;
the appointment ID, appointment patient ID, reason, and status are SQL NULL
(Python `None`). No dummy appointment is inserted. The highlighted NULL row on
the web page is the direct SQL result.

Filtering `a.status` in WHERE would remove Carlo's unmatched row. For a report
that keeps all patients but matches only scheduled appointments, write:

```sql
LEFT JOIN appointment AS a
  ON p.patient_id = a.patient_id AND a.status = 'Scheduled'
```

That differs from filtering the complete join result by scheduled status.
The actual activity queries keep all appointment statuses.

## SQL, Django, and portability

See [the runnable SQL examples](sql_joins_examples.sql): the two required queries
and two optional extensions (full appointment details; patients with no visits).
Those statements can be pasted individually into the Supabase SQL Editor after
the sample command has run against that same database.

In Django, the actual SQL and its parameters live in `apps/joins/queries.py`.
`connection.cursor()` executes each SELECT; `cursor.description` supplies the
column names, and `fetchall()` supplies the rows rendered by the template.
No ORM JOIN type is claimed: the page displays the exact raw query template used.
The command `verify_join_demo` prints both templates, parameters, and results.

Six unquoted `%s` placeholders bind the three school IDs and three fake emails.
Pass values separately to `cursor.execute(sql, QUERY_PARAMS)` rather than using
Python string interpolation. Django adapts these positional placeholders for
SQLite too. Double-quote `"user"` because PostgreSQL has a USER keyword. The `||`
operator concatenates names on PostgreSQL and SQLite.

These selected JOINs do not need a database-specific emulation. Verify your
database's support before choosing other types. SQLite RIGHT/FULL support is
version-dependent; neither is used here. PostgreSQL execution is checked
separately from the isolated SQLite test suite. Browser automation is unavailable
in this session: review the page's visual layout yourself. A running local server
was checked through HTTP for login, results, and successful CSS responses.

## Run and review

From the project root in PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
python manage.py check
python manage.py seed_join_demo
python manage.py verify_join_demo
python manage.py runserver
```

Visit `http://127.0.0.1:8000/login/`, sign in with your normal account, and open
`http://127.0.0.1:8000/joins/` or choose **SQL joins** in the navigation.
No new migrations are required. If setting up a new database, apply the existing
migrations with `python manage.py migrate` before seeding.

You may safely rerun `seed_join_demo`: identical records are reused. Conflicting
sample values or extra sample appointments cause an error and transaction
rollback; resolve the specific reported sample conflict instead of deleting all
users or appointments. Visiting `/joins/` executes SELECTs only.

For isolated tests, use a separate terminal; this environment override persists
until that terminal closes:

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'
.\venv\Scripts\python.exe manage.py test
```

Review these points before requesting the recording plan:

- All source rows are fictional; patient and appointment foreign keys match.
- INNER JOIN shows 3 rows, with Ana twice and Ben once; Carlo is absent.
- LEFT JOIN shows 4 rows; Carlo's appointment columns say NULL.
- The SQL and separate parameter list are visible and readable.
- The database badge names the backend actually running the page.
- All five live verification checks pass.
- Explain the result yourself and ask about any part you do not understand.

The personal recording, Google Drive upload, sharing check, and direct video-link
submission are for the student to perform. The instructor requires the actual
video file link, not a folder link. A conversational script and screen cues are
now available in [the video script](sql_joins_video_script.md).

## Research sources

- Instructor's supplied `Student_Guide_SQL_Joins_Django.pdf`, especially Parts 2,
  5, 6, 8, and 9.
- [PostgreSQL: joined tables and ON versus WHERE](https://www.postgresql.org/docs/current/queries-table-expressions.html#QUERIES-JOIN).
- [Django 4.2: executing custom SQL directly and placeholders](https://docs.djangoproject.com/en/4.2/topics/db/sql/#executing-custom-sql-directly).

Use the instructor guide for assessment requirements and these official
references for query behavior. The clinic examples and implementation are
adapted to TeknoCare's actual schema.
