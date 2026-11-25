"""Isolated, fast SQLite tests with no hosted configuration or email delivery."""
from .settings_base import *


SECRET_KEY = "teknocare-isolated-tests-only"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
TEKNOCARE_LOCAL_DEMO = True
TEKNOCARE_MAKE_PORTAL = False
