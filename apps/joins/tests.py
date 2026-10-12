from datetime import timedelta
from io import StringIO

import sqlparse
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.register.models import Appointment, Patient, Provider, Slot, User

from .demo_data import PATIENT_SAMPLES, seed_demo_data
from .queries import INNER_JOIN_SQL, LEFT_JOIN_SQL, execute_read_query, get_join_results
from .views import join_demo


class JoinQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.patients, cls.appointments = seed_demo_data()
        cls.viewer = User.objects.create_user(
            school_id="JOIN-TEST-VIEWER", email="viewer@example.invalid",
            fname="Review", lname="Student", password="test-password-123",
            user_type=User.UserType.PATIENT, account_status=User.AccountStatus.ACTIVE,
        )

    def test_inner_join_returns_each_matching_appointment(self):
        rows = execute_read_query(INNER_JOIN_SQL)
        self.assertEqual([row["patient_name"] for row in rows], ["Ana Reyes", "Ana Reyes", "Ben Santos"])
        self.assertEqual(len({row["appointment_id"] for row in rows}), 3)
        self.assertTrue(all(row["patient_id"] == row["appointment_patient_id"] for row in rows))
        self.assertNotIn("Carlo Lim", [row["patient_name"] for row in rows])

    def test_left_join_retains_unmatched_patient_with_actual_nulls(self):
        rows = execute_read_query(LEFT_JOIN_SQL)
        self.assertEqual([row["patient_name"] for row in rows], ["Ana Reyes", "Ana Reyes", "Ben Santos", "Carlo Lim"])
        carlo = rows[-1]
        self.assertEqual(carlo["patient_id"], self.patients[2].pk)
        for key in ("appointment_id", "appointment_patient_id", "reason_for_visit", "status"):
            self.assertIsNone(carlo[key])

    def test_queries_exclude_unrelated_clinic_data(self):
        patient = Patient.objects.create(
            patient=self.viewer, emergency_contact="Unrelated contact",
            medical_history_summary="Unrelated record", no_show_count=0,
        )
        sample_slot = self.appointments[0].slot
        slot = Slot.objects.create(
            provider=sample_slot.provider, start_time=sample_slot.start_time + timedelta(days=1),
            end_time=sample_slot.end_time + timedelta(days=1), is_booked=True,
        )
        Appointment.objects.create(
            patient=patient, provider=sample_slot.provider, slot=slot,
            reason_for_visit="Private unrelated visit", status=Appointment.Status.SCHEDULED,
        )
        results = get_join_results()
        self.assertTrue(results["verified"])
        self.assertNotIn(patient.pk, [row["patient_id"] for row in results["left_rows"]])

    def test_missing_appointment_changes_live_verification(self):
        self.appointments[0].delete()
        self.assertFalse(get_join_results()["verified"])

    def test_changed_sample_name_invalidates_explanations(self):
        User.objects.filter(pk=self.patients[0].pk).update(fname="Changed")
        self.assertFalse(get_join_results()["verified"])

    def test_page_requires_login(self):
        url = reverse("joins:demo")
        self.assertRedirects(self.client.get(url), f"{reverse('login:login')}?next={url}")

    def test_page_displays_sql_results_and_null_explanation(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("joins:demo"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "joins/join_demo.html")
        self.assertTrue(response.context["verified"])
        self.assertContains(response, "INNER JOIN appointment")
        self.assertContains(response, "LEFT JOIN appointment")
        self.assertContains(response, '<span class="null-value">NULL</span>', count=4, html=True)
        self.assertContains(response, "All checks passed")

    def test_opening_page_executes_only_read_queries(self):
        request = RequestFactory().get(reverse("joins:demo"))
        request.user = self.viewer
        with CaptureQueriesContext(connection) as captured:
            response = join_demo(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(captured), 3)
        self.assertTrue(all(query["sql"].lstrip().upper().startswith("SELECT") for query in captured))

    def test_seed_command_is_repeatable_and_does_not_delete_other_accounts(self):
        before = {model: model.objects.count() for model in (User, Patient, Provider, Slot, Appointment)}
        output = StringIO()
        call_command("seed_join_demo", stdout=output)
        call_command("seed_join_demo", stdout=output)
        self.assertEqual(before, {model: model.objects.count() for model in before})
        self.assertTrue(User.objects.filter(pk=self.viewer.pk).exists())
        self.assertNotIn("FAIL:", output.getvalue())

    def test_demo_accounts_cannot_login(self):
        for sample in PATIENT_SAMPLES:
            user = User.objects.get(school_id=sample[0])
            self.assertFalse(user.is_active)
            self.assertFalse(user.check_password("test-password-123"))

    def test_standalone_sql_examples_run_on_the_project_schema(self):
        sql_file = settings.BASE_DIR / "docs" / "sql_joins_examples.sql"
        statements = sqlparse.split(sql_file.read_text(encoding="utf-8"))
        self.assertEqual(len(statements), 4)
        outputs = []
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
                columns = [column[0] for column in cursor.description]
                outputs.append([dict(zip(columns, row)) for row in cursor.fetchall()])
        self.assertEqual(outputs[0], execute_read_query(INNER_JOIN_SQL))
        self.assertEqual(outputs[1], execute_read_query(LEFT_JOIN_SQL))
        self.assertEqual(len(outputs[2]), 3)
        self.assertEqual({row["provider_name"] for row in outputs[2]}, {"Maya Cruz"})
        self.assertEqual(len({row["start_time"] for row in outputs[2]}), 3)
        self.assertEqual(outputs[3], [{"patient_id": self.patients[2].pk, "patient_name": "Carlo Lim"}])

    def test_verification_command_displays_results(self):
        output = StringIO()
        call_command("verify_join_demo", stdout=output)
        self.assertIn("Rows returned: 3", output.getvalue())
        self.assertIn("Rows returned: 4", output.getvalue())
        self.assertIn("NULL", output.getvalue())


class JoinSetupTests(TestCase):
    def test_empty_database_reports_missing_samples_without_writing(self):
        self.assertFalse(get_join_results()["verified"])
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_verification_command_fails_for_missing_samples(self):
        with self.assertRaisesMessage(CommandError, "JOIN verification failed"):
            call_command("verify_join_demo", stdout=StringIO())

    def test_reserved_account_conflict_rolls_back_new_samples(self):
        User.objects.create_user(
            school_id=PATIENT_SAMPLES[1][0], email="existing@example.invalid",
            fname="Existing", lname="Person", password="test-password-123",
            user_type=User.UserType.PATIENT, account_status=User.AccountStatus.ACTIVE,
        )
        with self.assertRaisesMessage(CommandError, "No existing account will be overwritten"):
            seed_demo_data()
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 0)
        self.assertFalse(User.objects.filter(school_id=PATIENT_SAMPLES[0][0]).exists())
