"""Run the repeatable project checks against isolated in-memory SQLite."""
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    environment = os.environ.copy()
    environment["DJANGO_SETTINGS_MODULE"] = "config.settings_test"
    checks = [
        ("Dependency consistency", ["-m", "pip", "check"]),
        ("Django system checks", ["manage.py", "check", "--settings=config.settings_test"]),
        ("Migration drift", ["manage.py", "makemigrations", "--check", "--dry-run", "--settings=config.settings_test"]),
        ("Feature tests", ["manage.py", "test", "--noinput", "--settings=config.settings_test"]),
        ("ERD model agreement", ["scripts/verify_erd_models.py"]),
        ("Populated legacy upgrade", ["scripts/verify_erd_upgrade.py"]),
    ]
    for label, arguments in checks:
        print(f"\nChecking: {label}", flush=True)
        result = subprocess.run([sys.executable, *arguments], cwd=ROOT, env=environment)
        if result.returncode:
            print(f"FAILED: {label}. Stop and review the error before committing.", flush=True)
            return result.returncode
    print("\nAll isolated project checks passed. Supabase was not used.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
