# TeknoCare defense and demonstration script

Prepare the local database and accounts in the
[Step 14 guide](step_14_verification.md). Use fictional names, account IDs and
clinical examples throughout the demonstration.

| On screen | What to say |
| --- | --- |
| Sign in as **DEMO-ADMIN** and open **Clinic setup**. Show the provider designations, room and term. | “TeknoCare is a school prototype for the CIT-University clinic. The Admin sets up providers, rooms and terms. Clinical permissions depend on the provider's designation and assignment.” |
| Sign in as **DEMO-STUDENT**, then open **My appointments**. Book the slot created during setup. You can cancel and rebook to show both states in history. | “A Student sees available times, books a slot and manages their own appointment. The clinic keeps the canceled appointment in history.” |
| As **DEMO-ADMIN**, check in the Student in **Reception queue**, then open the encounter for **DEMO-DOCTOR**. If the slot is on a later clinic day, use **Walk-in** to show reception today and leave the booking as a separate example. | “Reception opens a Draft encounter for the attending provider. Students are eligible for tuition charges. Faculty and Staff visits are free.” |
| Sign in as **DEMO-NURSE**, find the Draft in **Clinical encounters** and save one fictional vital. | “The Nurse can record vitals for this encounter. Consultation notes and finalization are available to the assigned clinician.” |
| As **DEMO-DOCTOR**, save a fictional chief complaint, examination note and treatment plan. Check **Fictional demo finding** and choose it as the primary diagnosis. Add a referral to a fictional desk, then start a prescription draft. Add **Fictional demo item** with training-only item text and confirm issuance before finalizing. | “The attending Physician records the consultation, adds a patient-facing referral, and issues a prototype prescription. Finalizing releases the visit summary and completes the linked appointment.” |
| As **DEMO-STUDENT**, open **My visit summaries**, then **My prescriptions**. Open the print preview if useful. | “The signed-in Patient can see their finalized summary and issued prescription. Internal examination notes stay in the clinical workspace. The print copy is for this prototype.” |
| As **DEMO-ADMIN**, use **Tuition charges → Find an encounter** and create a PHP 100.00 line for the finalized Student visit. Export Pending CSV. Open the charge and confirm simulated posting. Optionally confirm simulated reversal with a fictional administrative reason. | “Exporting a charge preserves Pending status. A separate simulation records a posting acknowledgment using a demo reference. A reversal preserves the original posting history. The prototype does not collect payments or contact university finance.” |
| Open **Audit history** and **Operational reports**. Filter the audit by action and the reports by the demo term. | “The audit trail records who performed an action and which record it affected. Reports show aggregate counts and separate Pending, Posted and Voided tuition amounts.” |
| Show the checked-in ERD and point to the appointment, medical record and charge relationships. | “The Django models follow the 22-entity ERD. An appointment can link to one encounter. A walk-in can have an encounter without an appointment. Charges link to the encounter and academic term, and use the affiliation captured at the visit.” |

For the personnel example, open a Faculty or Staff walk-in as **DEMO-ADMIN**
and assign **DEMO-DENTIST**. After finalization, open billing for that encounter
and show the free-care message. The Admin's own secondary Staff Patient profile
can receive care from an assigned clinician and open its own patient screens.

## Prototype limits to explain if asked

- Official student, personnel and provider ID formats and credentials are
  unconfirmed. The demonstration uses fictional accounts, dates and catalog
  entries. The seed does not verify enrollment or professional credentials.
- Tuition posting and reversal are simulations. Prescription copies are for
  training. Email delivery, recovery by email and institutional sign-on are
  outside this prototype.
- The app is presented locally. Hosted Supabase requires an authorized staged
  rehearsal with representative data, verified backups and a grants and RLS
  review. See the [migration checklist](supabase_migration_checklist.md).
- The [ERD](erd/README.md), [data dictionary](erd/data_dictionary.md) and
  [role matrix](access_policy.md) describe the design and access rules.
