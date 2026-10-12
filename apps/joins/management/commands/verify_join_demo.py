from django.core.management.base import BaseCommand, CommandError

from apps.joins.queries import get_join_results


class Command(BaseCommand):
    help = "Run both sample joins, print the SQL/results, and verify the 2/1/0 dataset (read-only)."

    def handle(self, *args, **options):
        results = get_join_results()
        self.stdout.write(f"Database backend: {results['database_vendor']}")
        self.stdout.write(f"Parameters: {results['query_params']}")
        for title, sql_key, rows_key in (
            ("INNER JOIN", "inner_sql", "inner_rows"),
            ("LEFT JOIN", "left_sql", "left_rows"),
        ):
            self.stdout.write(f"\n{title}\n{results[sql_key]}\n")
            rows = results[rows_key]
            if rows:
                columns = ("patient_id", "patient_name", "appointment_id", "appointment_patient_id", "reason_for_visit", "status")
                table = [list(columns)] + [
                    ["NULL" if row[key] is None else str(row[key]) for key in columns]
                    for row in rows
                ]
                widths = [max(len(row[index]) for row in table) for index in range(len(columns))]
                for row in table:
                    self.stdout.write(" | ".join(value.ljust(width) for value, width in zip(row, widths)))
            self.stdout.write(f"Rows returned: {len(rows)}")
        for check in results["checks"]:
            self.stdout.write(f"{'PASS' if check['passed'] else 'FAIL'}: {check['label']}")
        if not results["verified"]:
            raise CommandError("JOIN verification failed. Run seed_join_demo or investigate the sample dataset.")
