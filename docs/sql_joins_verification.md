# SQL JOIN verification evidence

Verified on 2026-10-12 using the existing TeknoCare project.

## Completed checks

- Python 3.12.10; Django 4.2.30.
- 27 tests passed using an isolated in-memory SQLite database, including the 12 existing account tests.
- Django system checks passed; `makemigrations --check --dry-run` reported no changes.
- Both parameterized activity queries ran against the configured Supabase PostgreSQL database.
- All four standalone SQL examples ran on PostgreSQL: row counts 3, 4, 3, and 1 respectively.
- Repeating the seed command on PostgreSQL left User/Patient/Provider/Slot/Appointment row counts unchanged.
- All five live JOIN-result checks passed.
- A separate local SQLite preview server passed HTTP login, `/joins/` rendering, expected result counts, four NULL cells, and successful responses for the page CSS and its imported profile CSS.
- The preview server was stopped after verification; the project's Supabase connection was not replaced.

## Review still needed

No browser surface was available for automation in this session, so visual layout/readability has not been inspected. Open `/joins/` in your browser to check it before recording. Recording, sharing, and submission remain for the later stage requested by the user.

## Actual PostgreSQL output

The following output is from the project's read-only `verify_join_demo` command, not an invented result. Primary keys reflect this database snapshot and can differ on another database. All displayed records are fictional.

```text
Database backend: postgresql
Parameters: ('JOIN-DEMO-001', 'JOIN-DEMO-002', 'JOIN-DEMO-003', 'ana@join-demo.example.invalid', 'ben@join-demo.example.invalid', 'carlo@join-demo.example.invalid')

INNER JOIN
SELECT p.patient_id,
       u.school_id,
       u.fname || ' ' || u.lname AS patient_name,
       a.appointment_id,
       a.patient_id AS appointment_patient_id,
       a.reason_for_visit,
       a.status
FROM patient AS p
INNER JOIN "user" AS u ON p.patient_id = u.user_id
INNER JOIN appointment AS a ON p.patient_id = a.patient_id
WHERE u.school_id IN (%s, %s, %s)
  AND u.email IN (%s, %s, %s)
ORDER BY u.school_id, a.appointment_id;
patient_id | patient_name | appointment_id | appointment_patient_id | reason_for_visit       | status   
2          | Ana Reyes    | 1              | 2                      | Routine check-up       | Scheduled
2          | Ana Reyes    | 2              | 2                      | Follow-up consultation | Completed
3          | Ben Santos   | 3              | 3                      | Health clearance       | Scheduled
Rows returned: 3

LEFT JOIN
SELECT p.patient_id,
       u.school_id,
       u.fname || ' ' || u.lname AS patient_name,
       a.appointment_id,
       a.patient_id AS appointment_patient_id,
       a.reason_for_visit,
       a.status
FROM patient AS p
INNER JOIN "user" AS u ON p.patient_id = u.user_id
LEFT JOIN appointment AS a ON p.patient_id = a.patient_id
WHERE u.school_id IN (%s, %s, %s)
  AND u.email IN (%s, %s, %s)
ORDER BY u.school_id, a.appointment_id;
patient_id | patient_name | appointment_id | appointment_patient_id | reason_for_visit       | status   
2          | Ana Reyes    | 1              | 2                      | Routine check-up       | Scheduled
2          | Ana Reyes    | 2              | 2                      | Follow-up consultation | Completed
3          | Ben Santos   | 3              | 3                      | Health clearance       | Scheduled
4          | Carlo Lim    | NULL           | NULL                   | NULL                   | NULL     
Rows returned: 4
PASS: Three sample patients are present.
PASS: INNER JOIN returns Ana twice, Ben once, and excludes Carlo.
PASS: LEFT JOIN returns four rows, retaining Carlo without an appointment.
PASS: Carlo's appointment columns are SQL NULL.
PASS: Every matched appointment belongs to the displayed patient.

```
