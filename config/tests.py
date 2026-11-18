import json
import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase


class IsolatedConfigurationTests(SimpleTestCase):
    def inspect_settings(self, module, **environment):
        child_environment = os.environ.copy()
        child_environment.update({
            "DJANGO_SETTINGS_MODULE": module,
            "DATABASE_URL": "invalid-hosted-connection-must-not-be-used",
            "SECRET_KEY": "",
            "DEBUG": "invalid-hosted-debug-must-not-be-used",
            "DATABASE_SSL_REQUIRE": "false",
            **environment,
        })
        result = subprocess.run(
            [sys.executable, "-c", (
                "import json; from django.conf import settings; "
                "print(json.dumps({'engine': settings.DATABASES['default']['ENGINE'], "
                "'name': str(settings.DATABASES['default']['NAME']), "
                "'debug': settings.DEBUG, 'timezone': settings.TIME_ZONE, "
                "'hosts': settings.ALLOWED_HOSTS, 'hashers': settings.PASSWORD_HASHERS}))"
            )],
            cwd=settings.BASE_DIR, env=child_environment, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_local_settings_ignore_hosted_environment_and_use_real_password_hashing(self):
        configured = self.inspect_settings("config.settings_local", TEKNOCARE_LOCAL_DB_PATH="tmp/config-test.sqlite3")
        self.assertEqual(configured["engine"], "django.db.backends.sqlite3")
        self.assertTrue(configured["name"].endswith("config-test.sqlite3"))
        self.assertTrue(configured["debug"])
        self.assertEqual(configured["timezone"], "Asia/Manila")
        self.assertNotIn("django.contrib.auth.hashers.MD5PasswordHasher", configured["hashers"])

    def test_test_settings_cannot_be_redirected_to_hosted_or_local_file_database(self):
        configured = self.inspect_settings("config.settings_test", TEKNOCARE_LOCAL_DB_PATH="do-not-use.sqlite3")
        self.assertEqual(configured["engine"], "django.db.backends.sqlite3")
        self.assertEqual(configured["name"], ":memory:")
        self.assertFalse(configured["debug"])

    def test_environment_configuration_defaults_to_non_debug_and_parses_hosts(self):
        configured = self.inspect_settings(
            "config.settings", SECRET_KEY="isolated-configuration-test-key", DEBUG="false",
            DATABASE_URL="sqlite:///:memory:", ALLOWED_HOSTS=" localhost,127.0.0.1, ",
        )
        self.assertFalse(configured["debug"])
        self.assertEqual(configured["hosts"], ["localhost", "127.0.0.1"])
