from django.core.management.base import BaseCommand, CommandError

from apps.joins.demo_data import seed_demo_data
from apps.joins.queries import get_join_results


class Command(BaseCommand):
    help = "Add/reuse fictional SQL JOIN samples without deleting or overwriting existing records."

    def handle(self, *args, **options):
        patients, appointments = seed_demo_data()
        self.stdout.write(self.style.SUCCESS(
            f"Samples ready: {len(patients)} patients, 1 provider, 3 slots, {len(appointments)} appointments."
        ))
        self.stdout.write("Sample accounts use JOIN-DEMO IDs, fake emails, and cannot sign in.")
        results = get_join_results()
        for check in results["checks"]:
            label = "PASS" if check["passed"] else "FAIL"
            self.stdout.write(f"{label}: {check['label']}")
        if not results["verified"]:
            raise CommandError("The SQL results do not match the expected samples. Review the checks above.")
        self.stdout.write("Sign in with your normal account, then open /joins/.")
