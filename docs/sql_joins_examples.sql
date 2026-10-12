-- TeknoCare SQL JOIN activity. All statements are read-only SELECT queries.
-- Run python manage.py seed_join_demo first using the project's configured DB.
-- These literal sample values are for pasting into the Supabase SQL Editor.
-- Django uses the parameterized equivalents in apps/joins/queries.py.
-- Auto-generated patient/appointment IDs depend on your existing database.

-- REQUIRED EXAMPLE 1: INNER JOIN. Expected: Ana twice, Ben once (3 rows).
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
WHERE u.school_id IN ('JOIN-DEMO-001', 'JOIN-DEMO-002', 'JOIN-DEMO-003')
  AND u.email IN ('ana@join-demo.example.invalid', 'ben@join-demo.example.invalid', 'carlo@join-demo.example.invalid')
ORDER BY u.school_id, a.appointment_id;

-- REQUIRED EXAMPLE 2: LEFT JOIN. Expected: same matches + Carlo with NULL (4 rows).
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
WHERE u.school_id IN ('JOIN-DEMO-001', 'JOIN-DEMO-002', 'JOIN-DEMO-003')
  AND u.email IN ('ana@join-demo.example.invalid', 'ben@join-demo.example.invalid', 'carlo@join-demo.example.invalid')
ORDER BY u.school_id, a.appointment_id;

-- OPTIONAL EXTENSION 3: Appointment details with a patient, provider, and time slot.
-- Two aliases of "user" supply the names for different roles.
-- Expected: the 3 fictional appointments with provider Maya Cruz and distinct times.
SELECT a.appointment_id,
       patient_user.fname || ' ' || patient_user.lname AS patient_name,
       provider_user.fname || ' ' || provider_user.lname AS provider_name,
       pr.specialization,
       s.start_time,
       a.reason_for_visit
FROM appointment AS a
INNER JOIN patient AS p ON a.patient_id = p.patient_id
INNER JOIN "user" AS patient_user ON p.patient_id = patient_user.user_id
INNER JOIN provider AS pr ON a.provider_id = pr.provider_id
INNER JOIN "user" AS provider_user ON pr.provider_id = provider_user.user_id
INNER JOIN slot AS s ON a.slot_id = s.slot_id
WHERE patient_user.school_id IN ('JOIN-DEMO-001', 'JOIN-DEMO-002', 'JOIN-DEMO-003')
  AND patient_user.email IN ('ana@join-demo.example.invalid', 'ben@join-demo.example.invalid', 'carlo@join-demo.example.invalid')
ORDER BY patient_user.school_id, a.appointment_id;

-- OPTIONAL EXTENSION 4: Patients who have no appointments (LEFT JOIN + IS NULL).
-- Expected: Carlo only. Checking a non-nullable PK distinguishes an absent match.
SELECT p.patient_id, u.fname || ' ' || u.lname AS patient_name
FROM patient AS p
INNER JOIN "user" AS u ON p.patient_id = u.user_id
LEFT JOIN appointment AS a ON p.patient_id = a.patient_id
WHERE u.school_id IN ('JOIN-DEMO-001', 'JOIN-DEMO-002', 'JOIN-DEMO-003')
  AND u.email IN ('ana@join-demo.example.invalid', 'ben@join-demo.example.invalid', 'carlo@join-demo.example.invalid')
  AND a.appointment_id IS NULL
ORDER BY u.school_id;
