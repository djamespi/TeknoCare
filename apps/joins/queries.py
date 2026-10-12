"""Read-only, parameterized JOIN examples on the actual ERD table names."""

from collections import Counter

from django.db import connection

from .demo_data import APPOINTMENT_SAMPLES, PATIENT_SAMPLES


QUERY_PARAMS = (
    tuple(sample[0] for sample in PATIENT_SAMPLES)
    + tuple(sample[3] for sample in PATIENT_SAMPLES)
)

INNER_JOIN_SQL = """SELECT p.patient_id,
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
ORDER BY u.school_id, a.appointment_id;"""

LEFT_JOIN_SQL = """SELECT p.patient_id,
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
ORDER BY u.school_id, a.appointment_id;"""

PATIENT_SOURCE_SQL = """SELECT p.patient_id, u.school_id,
       u.fname || ' ' || u.lname AS patient_name
FROM patient AS p
INNER JOIN "user" AS u ON p.patient_id = u.user_id
WHERE u.school_id IN (%s, %s, %s)
  AND u.email IN (%s, %s, %s)
ORDER BY u.school_id;"""


def execute_read_query(sql):
    # Values are passed separately; never insert request data into SQL strings.
    with connection.cursor() as cursor:
        cursor.execute(sql, QUERY_PARAMS)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_join_results():
    patients = execute_read_query(PATIENT_SOURCE_SQL)
    inner_rows = execute_read_query(INNER_JOIN_SQL)
    left_rows = execute_read_query(LEFT_JOIN_SQL)
    expected = Counter(
        (
            PATIENT_SAMPLES[index][0],
            f"{PATIENT_SAMPLES[index][1]} {PATIENT_SAMPLES[index][2]}",
            reason,
            status,
        )
        for index, reason, status in APPOINTMENT_SAMPLES
    )
    result_fields = ("school_id", "patient_name", "reason_for_visit", "status")
    actual_inner = Counter(tuple(row[key] for key in result_fields) for row in inner_rows)
    actual_left = Counter(tuple(row[key] for key in result_fields) for row in left_rows)
    expected_left = expected + Counter({(PATIENT_SAMPLES[2][0], "Carlo Lim", None, None): 1})
    null_rows = [row for row in left_rows if row["appointment_id"] is None]
    correct_nulls = (
        len(null_rows) == 1
        and null_rows[0]["school_id"] == PATIENT_SAMPLES[2][0]
        and all(
            null_rows[0][key] is None
            for key in ("appointment_patient_id", "reason_for_visit", "status")
        )
    )
    correct_keys = bool(inner_rows) and all(
        row["patient_id"] == row["appointment_patient_id"]
        for row in inner_rows + left_rows
        if row["appointment_id"] is not None
    )
    checks = [
        {"label": "Three sample patients are present.", "passed": len(patients) == 3},
        {"label": "INNER JOIN returns Ana twice, Ben once, and excludes Carlo.", "passed": actual_inner == expected},
        {"label": "LEFT JOIN returns four rows, retaining Carlo without an appointment.", "passed": actual_left == expected_left},
        {"label": "Carlo's appointment columns are SQL NULL.", "passed": correct_nulls},
        {"label": "Every matched appointment belongs to the displayed patient.", "passed": correct_keys},
    ]
    return {
        "patients": patients,
        "appointments": inner_rows,
        "inner_rows": inner_rows,
        "left_rows": left_rows,
        "checks": checks,
        "verified": all(check["passed"] for check in checks),
        "inner_sql": INNER_JOIN_SQL,
        "left_sql": LEFT_JOIN_SQL,
        "query_params": QUERY_PARAMS,
        "database_vendor": connection.vendor,
    }
