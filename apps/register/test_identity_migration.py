from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class IdentityMigrationTests(TransactionTestCase):
    def test_ambiguous_legacy_identities_stop_upgrade_without_rewriting_data(self):
        previous = [("register", "0003_user_created_at_user_user_role_valid_and_more")]
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        executor.migrate(previous)
        old_users = executor.loader.project_state(previous).apps.get_model("register", "User")
        common = dict(fname="Fictional", lname="Legacy", password_hash="!", user_type="Admin", account_status="Active")
        first = old_users.objects.create(school_id="001-AbC", email="original@example.invalid", **common)
        duplicate = None
        try:
            for school_id, email, label in ((" 001-AbC ", "other@example.invalid", "university ID"),
                ("OTHER", " ORIGINAL@EXAMPLE.INVALID ", "email")):
                duplicate = old_users.objects.create(school_id=school_id, email=email, **common)
                with self.subTest(label=label), self.assertRaisesMessage(RuntimeError, f"duplicate normalized {label}"):
                    MigrationExecutor(connection).migrate(latest)
                first.refresh_from_db()
                duplicate.refresh_from_db()
                self.assertEqual((first.school_id, first.email), ("001-AbC", "original@example.invalid"))
                self.assertEqual((duplicate.school_id, duplicate.email), (school_id, email))
                with connection.cursor() as cursor:
                    cursor.execute('DELETE FROM "user" WHERE user_id = %s', [duplicate.pk])
                duplicate = None
        finally:
            if duplicate is not None:
                with connection.cursor() as cursor:
                    cursor.execute('DELETE FROM "user" WHERE user_id = %s', [duplicate.pk])
            MigrationExecutor(connection).migrate(latest)
        first.refresh_from_db()
        self.assertEqual(first.school_id, "001-AbC")
