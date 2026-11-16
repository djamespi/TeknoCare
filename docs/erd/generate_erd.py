"""Build the proposed ERD's DOT source and data dictionary using only Python stdlib.

Render DOT with Graphviz; see README.md for PNG export instructions.
This is design documentation, not a database migration.
"""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOMAINS = {
    "identity": ("Accounts & university", "#19343d", "#eff5f6"),
    "patient": ("Patient information", "#117c77", "#eef9f7"),
    "booking": ("Scheduling", "#365ca1", "#f0f4fc"),
    "clinical": ("Clinical care", "#77519b", "#f7f2fb"),
    "medicine": ("Prescriptions", "#a36826", "#fcf5e9"),
    "operations": ("Accountability", "#596674", "#f2f4f6"),
}

# Fields: key | column | PostgreSQL type | nullability. PK IDs are identity columns
# unless they also carry FK. UQ is a single-column UNIQUE constraint.
TABLES = {}


def table(name, domain, rows):
    TABLES[name] = (domain, [tuple(s.strip() for s in row.split("|"))
                              for row in rows.strip().splitlines()])


table("department", "identity", """
PK | department_id | integer | NN
UQ | code | varchar(20) | NN
 | name | varchar(120) | NN
 | is_active | boolean | NN
"""
)
table("user", "identity", """
PK | user_id | integer | NN
UQ | school_id | varchar(20) | NN
 | fname | varchar(50) | NN
 | lname | varchar(50) | NN
UQ | email | varchar(100) | NN
 | password_hash | varchar(255) | NN
 | user_type | varchar(10) | NN
 | account_status | varchar(10) | NN
 | created_at | timestamptz | NN
"""
)
table("patient", "patient", """
PK,FK | patient_id | integer | NN
FK | department_id | integer | NULL
 | affiliation | varchar(10) | NN
 | date_of_birth | date | NULL
 | medical_history_summary | text | NULL
 | created_at | timestamptz | NN
"""
)
table("provider", "clinical", """
PK,FK | provider_id | integer | NN
 | provider_type | varchar(20) | NN
UQ | license_number | varchar(50) | NULL
 | specialization | varchar(100) | NULL
 | is_active | boolean | NN
"""
)
table("user_profile", "identity", """
PK,FK | user_id | integer | NN
 | phone_number | varchar(30) | NULL
 | home_address | text | NULL
 | bio | text | NULL
"""
)
table("user_settings", "identity", """
PK,FK | user_id | integer | NN
 | dark_mode | boolean | NN
 | email_notifications | boolean | NN
"""
)
table("emergency_contact", "patient", """
PK | contact_id | integer | NN
FK | patient_id | integer | NN
 | full_name | varchar(150) | NN
 | relationship | varchar(50) | NN
 | phone_number | varchar(30) | NN
 | is_primary | boolean | NN
"""
)
table("patient_allergy", "patient", """
PK | allergy_id | integer | NN
FK | patient_id | integer | NN
 | allergen | varchar(150) | NN
 | reaction | text | NULL
 | severity | varchar(15) | NN
 | recorded_at | timestamptz | NN
"""
)
table("clinic_room", "booking", """
PK | room_id | integer | NN
 | campus | varchar(100) | NN
 | building | varchar(100) | NN
 | room_number | varchar(20) | NN
 | is_active | boolean | NN
"""
)
table("slot", "booking", """
PK | slot_id | integer | NN
FK | provider_id | integer | NN
FK | room_id | integer | NN
 | start_time | timestamptz | NN
 | end_time | timestamptz | NN
 | is_active | boolean | NN
"""
)
table("appointment", "booking", """
PK | appointment_id | integer | NN
FK | patient_id | integer | NN
FK | slot_id | integer | NN
 | reason_for_visit | text | NN
 | status | varchar(12) | NN
 | created_at | timestamptz | NN
 | canceled_at | timestamptz | NULL
"""
)
table("medical_record", "clinical", """
PK | record_id | integer | NN
FK,UQ | appointment_id | integer | NULL
FK | patient_id | integer | NN
FK | provider_id | integer | NN
 | chief_complaint | text | NN
 | symptoms | text | NULL
 | examination_notes | text | NULL
 | treatment_plan | text | NULL
 | status | varchar(10) | NN
 | visited_at | timestamptz | NN
 | finalized_at | timestamptz | NULL
"""
)
table("vital_sign", "clinical", """
PK | vital_id | integer | NN
FK | record_id | integer | NN
FK | recorded_by_user_id | integer | NN
 | recorded_at | timestamptz | NN
 | temperature_c | numeric(4,1) | NULL
 | systolic_mmhg | smallint | NULL
 | diastolic_mmhg | smallint | NULL
 | pulse_bpm | smallint | NULL
 | respiratory_rate | smallint | NULL
 | oxygen_saturation_pct | numeric(5,2) | NULL
 | height_cm | numeric(5,2) | NULL
 | weight_kg | numeric(6,2) | NULL
"""
)
table("diagnosis", "clinical", """
PK | diagnosis_id | integer | NN
UQ | code | varchar(20) | NN
 | description | varchar(255) | NN
 | coding_system | varchar(30) | NN
"""
)
table("record_diagnosis", "clinical", """
PK,FK | record_id | integer | NN
PK,FK | diagnosis_id | integer | NN
 | is_primary | boolean | NN
 | notes | text | NULL
"""
)
table("medication", "medicine", """
PK | medication_id | integer | NN
UQ | medication_code | varchar(30) | NN
 | generic_name | varchar(150) | NN
 | strength | varchar(50) | NN
 | dosage_form | varchar(50) | NN
 | is_active | boolean | NN
"""
)
table("prescription", "medicine", """
PK | prescription_id | integer | NN
FK | record_id | integer | NN
FK | prescriber_id | integer | NN
 | issued_at | timestamptz | NN
 | status | varchar(10) | NN
"""
)
table("prescription_item", "medicine", """
PK | item_id | integer | NN
FK | prescription_id | integer | NN
FK | medication_id | integer | NN
 | dose | varchar(100) | NN
 | route | varchar(50) | NN
 | frequency | varchar(100) | NN
 | duration_days | smallint | NN
 | quantity | numeric(10,2) | NN
 | quantity_unit | varchar(30) | NN
 | instructions | text | NULL
"""
)
table("referral", "clinical", """
PK | referral_id | integer | NN
FK | record_id | integer | NN
FK | referred_by_provider_id | integer | NN
 | destination | varchar(200) | NN
 | reason | text | NN
 | status | varchar(12) | NN
 | referred_at | timestamptz | NN
"""
)
table("audit_log", "operations", """
PK | log_id | integer | NN
FK | actor_user_id | integer | NULL
 | action_performed | varchar(100) | NN
 | target_table | varchar(50) | NN
 | target_record_id | integer | NN
 | logged_at | timestamptz | NN
"""
)

# (child table, child FK column, parent table, parent PK column, children per parent)
RELATIONS = [
    ("patient", "patient_id", "user", "user_id", "0..1"),
    ("provider", "provider_id", "user", "user_id", "0..1"),
    ("user_profile", "user_id", "user", "user_id", "0..1"),
    ("user_settings", "user_id", "user", "user_id", "0..1"),
    ("patient", "department_id", "department", "department_id", "0..*"),
    ("emergency_contact", "patient_id", "patient", "patient_id", "0..*"),
    ("patient_allergy", "patient_id", "patient", "patient_id", "0..*"),
    ("slot", "provider_id", "provider", "provider_id", "0..*"),
    ("slot", "room_id", "clinic_room", "room_id", "0..*"),
    ("appointment", "patient_id", "patient", "patient_id", "0..*"),
    ("appointment", "slot_id", "slot", "slot_id", "0..*"),
    ("medical_record", "appointment_id", "appointment", "appointment_id", "0..1"),
    ("medical_record", "patient_id", "patient", "patient_id", "0..*"),
    ("medical_record", "provider_id", "provider", "provider_id", "0..*"),
    ("vital_sign", "record_id", "medical_record", "record_id", "0..*"),
    ("vital_sign", "recorded_by_user_id", "user", "user_id", "0..*"),
    ("record_diagnosis", "record_id", "medical_record", "record_id", "0..*"),
    ("record_diagnosis", "diagnosis_id", "diagnosis", "diagnosis_id", "0..*"),
    ("prescription", "record_id", "medical_record", "record_id", "0..*"),
    ("prescription", "prescriber_id", "provider", "provider_id", "0..*"),
    ("prescription_item", "prescription_id", "prescription", "prescription_id", "0..*"),
    ("prescription_item", "medication_id", "medication", "medication_id", "0..*"),
    ("referral", "record_id", "medical_record", "record_id", "0..*"),
    ("referral", "referred_by_provider_id", "provider", "provider_id", "0..*"),
    ("audit_log", "actor_user_id", "user", "user_id", "0..*"),
]


def validate():
    fks = {(t, r[1]) for t, (_, rows) in TABLES.items() for r in rows if "FK" in r[0]}
    assert len(RELATIONS) == len(fks)
    assert {(r[0], r[1]) for r in RELATIONS} == fks
    for child, col, parent, pk, cardinality in RELATIONS:
        row = next(r for r in TABLES[child][1] if r[1] == col)
        target = next(r for r in TABLES[parent][1] if r[1] == pk)
        assert row[2] == target[2] and "PK" in target[0]
        assert cardinality in ("0..1", "0..*")


def html_table(name):
    domain, rows = TABLES[name]
    _, color, bg = DOMAINS[domain]
    parts = [f'<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5" COLOR="#d5dfe3" BGCOLOR="{bg}">',
             f'<TR><TD COLSPAN="4" BGCOLOR="{color}" PORT="title"><FONT COLOR="white" POINT-SIZE="14"><B>{name}</B></FONT></TD></TR>',
             '<TR><TD><B>Key</B></TD><TD ALIGN="LEFT"><B>Column</B></TD><TD ALIGN="LEFT"><B>PostgreSQL</B></TD><TD><B>Null?</B></TD></TR>']
    for key, col, typ, null in rows:
        parts.append(f'<TR><TD>{escape(key) or " "}</TD><TD PORT="{col}" ALIGN="LEFT">{escape(col)}</TD>'
                     f'<TD ALIGN="LEFT">{escape(typ)}</TD><TD>{null}</TD></TR>')
    return "".join(parts) + "</TABLE>"


def build():
    validate()
    lines = ['digraph TeknoCare {',
             'graph [rankdir=TB, bgcolor="white", pad="0.5", nodesep="0.75", ranksep="1.1", splines=polyline, outputorder=edgesfirst, fontname="Arial", labelloc=t, labeljust=l, newrank=true, concentrate=false];',
             'node [shape=plain, fontname="Arial", fontsize=11];',
             'edge [dir=both, color="#728795", penwidth=1.1, arrowsize=0.7, fontname="Arial", fontsize=9, fontcolor="#19343d", labeldistance=2];',
             'label=<<FONT POINT-SIZE="30" COLOR="#19343d"><B>TeknoCare | University Clinic</B></FONT><BR ALIGN="LEFT"/>'
             f'<FONT POINT-SIZE="16">Proposed physical ERD / PostgreSQL / {len(TABLES)} entities</FONT><BR ALIGN="LEFT"/>'
             '<FONT POINT-SIZE="12">PK = primary key   FK = foreign key   UQ = unique   NN = not null   NULL = optional</FONT><BR ALIGN="LEFT"/>'
             '<FONT POINT-SIZE="12">Relationship ends: 1 = exactly one   0..1 = optional one   0..* = zero or more</FONT><BR ALIGN="LEFT"/>'
             '<FONT POINT-SIZE="12">Each solid line represents a foreign key. Composite PK: record_diagnosis(record_id, diagnosis_id).</FONT><BR ALIGN="LEFT"/>'
             '<FONT POINT-SIZE="12">Slot may retain canceled bookings; only one non-canceled appointment per slot. See README for constraints.</FONT><BR ALIGN="LEFT"/>'
             '<FONT POINT-SIZE="12">Design proposal: application models and database have not been migrated.</FONT><BR ALIGN="LEFT"/><BR ALIGN="LEFT"/>'
             '<FONT POINT-SIZE="12" COLOR="#117c77">Teal: patients</FONT>  |  <FONT POINT-SIZE="12" COLOR="#365ca1">Blue: scheduling</FONT>  |  '
             '<FONT POINT-SIZE="12" COLOR="#77519b">Purple: clinical</FONT>  |  <FONT POINT-SIZE="12" COLOR="#a36826">Amber: prescriptions</FONT>>;']
    for name in TABLES:
        lines.append(f'"{name}" [label=<{html_table(name)}>];')
    for child, col, parent, pk, cardinality in RELATIONS:
        nullable = next(r[3] == "NULL" for r in TABLES[child][1] if r[1] == col)
        tail = "teeodot" if nullable else "teetee"
        head = "teeodot" if cardinality == "0..1" else "crowodot"
        # End on the outside of each entity; interior table-cell ports can hide
        # crow's feet behind the opaque HTML table in raster exports.
        lines.append(f'"{parent}" -> "{child}" [arrowtail={tail}, arrowhead={head}, '
                     f'taillabel="{"0..1" if nullable else "1"}", headlabel="{cardinality}"];')
    lines.append('}')
    (ROOT / "teknocare_improved_erd.dot").write_text("\n".join(lines) + "\n", encoding="utf-8")
    docs = ["# Proposed data dictionary", "", "Generated from `generate_erd.py`. This describes the proposed schema, not the live database.", "",
            "NN means NOT NULL. UQ means a single-column UNIQUE constraint. Non-FK primary keys use GENERATED BY DEFAULT AS IDENTITY. See README for additional constraints and deletion rules.", ""]
    for name, (domain, rows) in TABLES.items():
        docs += [f"## `{name}`", "", f"Domain: {DOMAINS[domain][0]}", "", "| Key | Column | PostgreSQL type | Nullability | References |", "| --- | --- | --- | --- | --- |"]
        for key, col, typ, null in rows:
            ref = next((f"`{p}.{pk}`" for c, f, p, pk, _ in RELATIONS if c == name and f == col), "")
            docs.append(f"| {key} | `{col}` | `{typ}` | {null} | {ref} |")
        docs.append("")
    (ROOT / "data_dictionary.md").write_text("\n".join(docs), encoding="utf-8")
    print(f"Validated {len(TABLES)} entities and {len(RELATIONS)} foreign keys. Generated DOT and data dictionary.")


if __name__ == "__main__":
    build()
