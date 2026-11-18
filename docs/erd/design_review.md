# ERD design and operational readiness review

Scope: the university clinic described in this conversation, with student fees added to tuition and free Faculty/Staff care. Review based on the proposed diagram, current Django models, migrations, and route/view definitions. No live clinical or finance data was queried and no database migrations were applied.

## Verdict

The 22-entity, 28-FK ERD now matches the feature models and migration target. It is **not a fully operational clinic system**: most clinical screens, granular permissions, finance procedures/integration, and PostgreSQL staging verification remain. Models, row constraints, selected cross-table guards, booking/billing services, and migration checks are implemented; see [model implementation](model_implementation.md) for the exact boundary. The assessment does not establish that every possible university clinic requirement has been collected.

## Findings addressed in the design

| Finding | Resolution |
| --- | --- |
| Student fees and free personnel care were not represented. | Added academic terms and positive student charge lines linked to medical records; personnel encounters have no charges. |
| Changing a person's current affiliation could change historical billing eligibility. | Capture immutable affiliation at the visit; charges use that historical eligibility. |
| Mutually exclusive profile rules prevented providers/admins from receiving care using their existing account. | Keep one primary interface role but permit a Patient profile for any account needing care. Clinical and finance permissions remain separate. |
| Export retries could produce duplicate tuition charges. | Stable unique charge code for idempotency, external acknowledgment references, and a documented reconciliation requirement. |
| A posted charge needed a correction path. | Preserve the original line; require confirmed reversal metadata before a posted charge becomes Voided. |
| Diagnosis codes could collide across coding systems. | Composite uniqueness on coding system and code, visible in both diagram and dictionary. |
| Composite uniqueness was hidden in prose. | Show room, diagnosis, and academic-term composite UNIQUE constraints in entity boxes. |
| The PNG exporter relied on hardcoded entity counts. | Validate rendered entity names and relationship pairs against the schema source. |

## Workflow coverage and current implementation

| Workflow | Model implementation | Remaining work |
| --- | --- | --- |
| Accounts/intake | User, Patient, Profile, Settings, contacts; atomic student registration and basic custom-user admin/session APIs | Verified staff intake, granular permissions, patient access rules |
| Scheduling | Room/Slot/Appointment, conditional uniqueness, PostgreSQL exclusions, booking/cancellation services | Role screens, complete state workflow, PostgreSQL concurrency verification |
| Clinical encounters | Scheduled/walk-in records, snapshot/appointment guards, vitals, diagnoses, referrals | Clinical screens, staff authorization, controlled amendments |
| Prescriptions | Catalog, header/items, model validation of issued history | Issuing workflow, granular prescriber authorization, bulk-write restrictions |
| Tuition charges | AcademicTerm/StudentCharge, billing guards and acknowledgment/reversal services | Screens, university export/integration and reconciliation procedure |
| Personnel care | Patient profiles may coexist with provider/admin access; personnel visits cannot be charged | Membership verification and staff intake interface |
| Audit/history | User-based append-only audit guards, restrictive references, legacy archives | Broader workflow audit coverage and retention/access procedures |

Current `config/urls.py` exposes account pages, Django admin, and dashboard. Step 0
removed the completed SQL JOIN learning page and app; its documents are archived
under `docs/archive/sql_joins/`. No clinic booking/encounter/prescription/billing
screens have been added. The migrations were verified on fresh/populated SQLite
databases; deployment to the configured database has not occurred.

## Required acceptance checks before calling the application operational

This is the end-to-end operational checklist. Some model-level cases are now covered by automated tests, but this list is not a claim that all production workflows passed:

1. Apply reviewed Django migrations on a disposable PostgreSQL database with representative fictional data. Verify all keys, nullable links, deletion protections, and legacy-data migration paths.
2. Exercise patient, provider, admin, and personnel-as-patient flows. Check per-record access and prevent unauthorized access to clinical notes and charge actions. Verify Django admin and password/session behavior explicitly.
3. Schedule visits, cancel and rebook, complete visits, and record walk-ins. Use concurrent requests to verify that one slot, provider, room, or patient cannot be double booked.
4. Record repeated vitals, multiple diagnoses, prescriptions, and referrals. Verify that invalid measurements and unauthorized finalization/issuing are rejected, and history is preserved after catalog/account changes.
5. Create a Student visit and Pending charge; successfully post exactly once to the correct student and academic term, with external/manual acknowledgment. Retrying the same code must not post twice.
6. Attempt charges for Faculty and Staff visits through both application and direct database writes. Reject both. Changing current affiliation must not silently alter existing visit eligibility.
7. Exercise Pending -> Voided and Posted -> confirmed reversal -> Voided. Reject invalid transitions, missing references, negative/zero charges, and edits to posted amounts. Simulate timeouts and reconciliation after an external success/local failure.
8. Verify clinical and billing reports agree with records, charge status, acknowledgments, and audit events. Confirm the application does not claim Posted charges are paid tuition.
9. Exercise backup/restore, account deactivation, and protected deletion. Test the actual running screens and capture the instructor's required screenshots after implementation.

Additional modules such as inventory/dispensing, laboratory orders, immunizations, file attachments, or detailed finance settlement require further scope decisions. They are not implied by the current ERD.

## Evidence collected for this documentation change

The generator validates key existence, FK target types, nullability, composite uniqueness column references, and relationship cardinality consistency. The exporter checks the SVG against the 22 entity names and 28 relationship pairs and produces the PNG. The rendered diagram is visually checked. These checks validate design artifacts, not production database behavior or an external billing service.

The existing Django application also passed `manage.py check` with a disposable in-memory SQLite configuration: no issues reported. This is a configuration/system check only; it neither exercises the proposed schema nor proves PostgreSQL constraints, Django admin login, or clinic/finance workflows work.

The model implementation adds feature tests, a populated-legacy SQLite upgrade check, and a metadata comparison for every ERD column/key/type/relationship. PostgreSQL-specific behavior is still a staging gate; read `model_implementation.md` for verification commands and limitations.
