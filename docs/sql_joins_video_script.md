# TeknoCare SQL JOIN video script and screen cues

Plan for approximately 8-10 minutes, including opening files and pointing to
results. Replace **[Your Name]** with your name. Read only the **Say** passages;
the **Do** passages are screen directions. You can shorten or rephrase the spoken
lines once you understand them. Pause briefly after important results so the
viewer can read them.

## Prepare before recording

1. Open a fresh PowerShell terminal at the TeknoCare project root. A fresh
   terminal avoids carrying over the in-memory SQLite override used for tests.
2. Activate the existing environment and verify the sample data:

   ```powershell
   .\venv\Scripts\Activate.ps1
   python manage.py check
   python manage.py seed_join_demo
   python manage.py verify_join_demo
   python manage.py runserver
   ```

   Samples are already in Supabase; rerunning the seed command reuses identical
   records. The verification output should say `postgresql`, return 3 and 4
   rows, and show five PASS checks. Resolve an error before recording instead
   of describing an expected result as though it appeared.
3. Sign in with your normal account and open `http://127.0.0.1:8000/joins/`.
   Confirm the page looks readable and says **All checks passed**. The fictional
   sample accounts cannot sign in.
4. Keep these files open in the IDE:
   - `apps/register/models.py`
   - `apps/joins/demo_data.py`
   - `apps/joins/queries.py`
   - `apps/joins/views.py`
5. Increase the editor/terminal font size and browser zoom enough to make the
   code and tables readable. Collapse unrelated folders and close `.env` or
   tabs containing credentials. Complete your login before recording.
6. Stop the server with Ctrl+C once you have checked the page. Your login session
   should remain available when you restart it during Scene 4. Keep the browser
   tab ready; the earlier page remains visible until you refresh it.

The recording uses the actual app and code. Slides and the Supabase dashboard
are optional; you do not need either to demonstrate the two required JOINs.

## 1. Introduce the project and your selected JOINs

**Do:** Start recording. Show the top of the `/joins/` page with its title and
database badge visible. Do not refresh until you have restarted the server in
Scene 4.

**Say:**

> Hi, I'm [Your Name]. For this activity, I'll demonstrate INNER JOIN and LEFT
> JOIN using my Django project, TeknoCare. It's a university clinic application,
> and its database is PostgreSQL hosted on Supabase.
>
> The project already has patient and appointment models, but the appointment
> section doesn't have its own interface yet. For this activity, I'm using a
> separate joins app to display the queries and their results.
>
> I'll use the same sample patients for both queries, so we can see exactly
> what changes when a patient has no appointment.

## 2. Show the model relationship

**Do:** Switch to `apps/register/models.py`. Use Ctrl+F for `class Patient`.
Point to its one-to-one User relation. Then find `class Appointment` and point
to `patient = models.ForeignKey(...)`, including `db_column="patient_id"`.
Keep the relevant lines visible while explaining them.

**Say:**

> Here are the existing models that the demonstration uses. Each patient has
> a linked user account, which stores their name and school ID.
>
> In the Appointment model, this patient field is a foreign key. It connects
> an appointment to a particular patient. One patient can have several
> appointments, but each appointment belongs to one patient.
>
> That gives us the condition for the join: the patient's primary key must
> match the appointment's patient ID. We aren't matching the patient ID with
> the appointment ID, because those identify different things.

**Do:** Briefly point to `Meta.db_table` for Patient and Appointment if visible.

**Say:**

> These models use the table names patient and appointment. The query also
> uses the user table to retrieve the patient's name.

## 3. Show and prepare the sample records

**Do:** Open `apps/joins/demo_data.py`. Show `PATIENT_SAMPLES` and
`APPOINTMENT_SAMPLES` near the top. Point to the two entries starting with `0`
and the entry starting with `1`.

**Say:**

> I have three fictional patients: Ana Reyes, Ben Santos, and Carlo Lim.
> Ana has two appointments, Ben has one, and Carlo has none.
>
> These zero and one values select Ana and Ben from the sample list. Their
> actual database IDs are assigned separately when the records are created.
>
> Carlo's missing appointment is intentional. It lets us see the difference
> between returning matching records and keeping every patient.
>
> The sample setup also provides a fictional provider and three slots, because
> those are required by the existing Appointment model.

**Do:** Switch to the activated terminal and run:

```powershell
python manage.py seed_join_demo
```

Wait for the command to finish and point to the sample totals and PASS lines.

**Say:**

> This command prepares the sample data. Since the same samples are already
> present, it reuses them. I can run it again without creating duplicate
> appointments or deleting existing clinic records.

## 4. Run Django and show the source data

**Do:** In the same terminal, run:

```powershell
python manage.py runserver
```

Wait for the server's startup message. Switch to the browser, refresh
`http://127.0.0.1:8000/joins/`, and click **Sample data**. Keep both source
tables visible. Point from a patient ID to matching appointment patient IDs.

**Say:**

> Now I'll run the application and refresh the demonstration page.
>
> This table shows the three sample patients. Beside it are the three
> appointments. The appointment's patient ID tells us which patient it belongs
> to. Here, two appointments refer to Ana, one refers to Ben, and none refer
> to Carlo.
>
> These are records read from the database. The IDs can be different on another
> database; what matters is that the related IDs match.

## 5. Show how Django executes and displays the SQL

**Do:** Open `apps/joins/queries.py`. Find `execute_read_query`. Point to
`connection.cursor()`, `cursor.execute(sql, QUERY_PARAMS)`, and `fetchall()`.
Then show `get_join_results()` calling the two query constants.

**Say:**

> For this activity, the queries use raw SQL through Django's database
> connection. This function executes the SQL, fetches the result rows, and
> makes them available to the page.
>
> The sample school IDs and emails are passed separately as parameters. The
> percent-s placeholders are where those values are bound. This also keeps
> the results limited to the fictional activity accounts.

**Do:** Open `apps/joins/views.py` and point to the `render(...)` line.

**Say:**

> The view calls get_join_results and sends that information to the template.
> The template displays the SQL and the returned rows. So refreshing the page
> runs the queries again; the displayed results aren't hardcoded in the HTML.

## 6. Demonstrate INNER JOIN

**Do:** Return to `apps/joins/queries.py` and show `INNER_JOIN_SQL`. Highlight:

```sql
FROM patient AS p
INNER JOIN "user" AS u ON p.patient_id = u.user_id
INNER JOIN appointment AS a ON p.patient_id = a.patient_id
```

**Say:**

> First is INNER JOIN. It returns a row for each pair that matches the join
> condition. In this example, that means patients who have appointments.
>
> The letters p, u, and a are aliases for patient, user, and appointment. The
> first join retrieves the patient's name from their user account. This next
> join matches the patient with their appointments using patient_id.
>
> For a clinic, this would be useful when preparing an appointment list with
> patient details.

**Do:** Switch to the browser and click **INNER JOIN**. Show the SQL, then scroll
to its result table. Point to Ana's two different appointment IDs, Ben's row,
and the **3 result rows** badge. Pause so the viewer can read them.

**Say:**

> Here we have three result rows. Ana appears twice because she has two
> different appointments. Ben appears once because he has one appointment.
> Carlo doesn't appear because he has no matching appointment.
>
> Ana's repeated name is expected. Each row represents a patient-appointment
> pair, so this is three appointments involving two distinct patients.

## 7. Demonstrate LEFT JOIN

**Do:** Show `LEFT_JOIN_SQL` in the editor. Highlight:

```sql
LEFT JOIN appointment AS a ON p.patient_id = a.patient_id
```

**Say:**

> Next is LEFT JOIN. The patient-to-appointment join now keeps every sample
> patient, even when there isn't a matching appointment.
>
> The condition stays the same. The user join also stays INNER JOIN, because
> every patient already has a required user account. The change we're
> comparing is specifically between patients and appointments.

**Do:** Switch to the browser and click **LEFT JOIN**. Show its SQL and result
table. Point to Carlo's highlighted row and each of his four NULL cells.

**Say:**

> This time we have four rows. Ana still appears twice, and Ben still appears
> once. But Carlo is now included.
>
> His patient ID and name are present, while his appointment columns contain
> NULL. That means there was no matching appointment. It doesn't mean an
> empty appointment was created or that his appointment ID is zero.
>
> This could be useful for a clinic report that includes all patients and
> helps identify people who haven't booked an appointment.
>
> The WHERE clause here only limits the fictional accounts. If I filtered
> appointment status in WHERE, Carlo's NULL row would be removed. To keep all
> patients while matching only a particular appointment status, that condition
> would go in the ON clause instead.

## 8. Show verification and close

**Do:** Click **Verification** in the page's section links, or scroll to
**Live verification**. Keep all five checks and the **All checks passed** badge
visible. Then briefly scroll back to the database badge if needed.

**Say:**

> These checks confirm the expected results: three rows for INNER JOIN,
> four for LEFT JOIN, Carlo's NULL appointment values, and matching patient
> IDs for the appointments that were returned.
>
> This demonstration is running on PostgreSQL. The two selected joins also
> work on SQLite, so these examples don't need an emulation or workaround.
>
> The difference we've seen is that INNER JOIN returns matching pairs, while
> LEFT JOIN also keeps patients without a match.
>
> This joins page is temporary for the activity. As I continue developing
> TeknoCare, I plan to remove the demonstration page and use these query
> concepts in the actual appointment features. The existing Patient and
> Appointment models will still be part of the project.
>
> That completes my demonstration. Thank you.

**Do:** Pause briefly on the result or verification table, then stop recording.

## Optional terminal proof

The browser already demonstrates both queries. If your instructor wants an
additional terminal run, open a second fresh terminal, activate the venv, and run:

```powershell
python manage.py verify_join_demo
```

**Say:**

> This read-only command runs the same two queries directly and prints their
> SQL, parameters, and results. It confirms the same three-row and four-row
> outputs shown in the browser.

Keep this optional segment short. Do not stop the server merely to run it in a
second terminal. The five live checks are different from the automated test
suite: the project previously passed 27 tests using an isolated SQLite database.

## Short answers if you are asked a follow-up

- **Why these JOIN types?** "They answer useful clinic questions, and Carlo's
  missing appointment makes their difference easy to demonstrate."
- **Why is Ana repeated?** "She has two matching appointment rows. The query
  returns one row per matching pair."
- **Why use User as well?** "The patient's name is stored in User, so that
  additional join retrieves the name."
- **Why is the user table quoted?** "USER is also a PostgreSQL keyword, so
  double quotes identify the table named user."
- **Why raw SQL?** "The activity allows ORM or raw SQL. Raw SQL makes the
  selected join types and their ON conditions explicit."
- **Why create another Django app?** "It organizes the activity page, queries,
  sample setup, and tests while the appointment UI is still being developed.
  A separate app isn't required for SQL JOINs."
- **Does removing the joins app remove the samples?** "No. The samples are
  stored through the existing models and would need separate cleanup."
- **Do the samples represent real patients?** "No. They are fictional activity
  records, with fake emails and accounts that cannot sign in."

## After recording: upload and submit

1. Watch the video and confirm your voice, SQL, code, and result tables are
   readable. Both JOINs must actually be shown running and explained.
2. Save it with a clear filename, such as `LASTNAME_SQL_JOIN_DEMO.mp4`.
3. Upload the video file to Google Drive. Open that specific file and choose
   **Share**.
4. Use **Anyone with the link** if your institution permits it; otherwise use
   the instructor's required access setting. Verify the instructor can view it.
5. Copy and submit the direct video-file link. Test its access in a private
   window or another account where appropriate. Do not submit the folder link.

Based on the supplied instructor guide and the project's implementation in
`apps/register/models.py`, `apps/joins/`, and `templates/joins/`. The live
PostgreSQL output was rechecked when this script was prepared. Visual browser
review remains a preparation step for the student because browser automation
was unavailable in this session.
