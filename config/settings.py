"""Explicit environment-backed configuration for reviewed hosted/staging use."""
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from .settings_base import *


load_dotenv(BASE_DIR / ".env")


def environment_boolean(name, default):
    value = os.environ.get(name, str(default)).strip().lower()
    if value not in {"true", "false", "1", "0"}:
        raise ImproperlyConfigured(f"{name} must be true, false, 1 or 0.")
    return value in {"true", "1"}


SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY or SECRET_KEY == "replace-with-a-generated-secret":
    raise ImproperlyConfigured("Set SECRET_KEY for config.settings; use config.settings_local for local development.")

DEBUG = environment_boolean("DEBUG", False)
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "").split(",") if host.strip()]

database_url = os.environ.get("DATABASE_URL", "").strip()
if not database_url:
    raise ImproperlyConfigured("Set DATABASE_URL for config.settings; use config.settings_local for a local SQLite database.")
try:
    DATABASES = {"default": dj_database_url.parse(
        database_url, conn_max_age=600,
        ssl_require=environment_boolean("DATABASE_SSL_REQUIRE", database_url.startswith(("postgres://", "postgresql://"))),
    )}
except (ValueError, KeyError):
    raise ImproperlyConfigured("DATABASE_URL is invalid; check the connection configuration.") from None

CLINIC_CURRENCY_CODE = os.environ.get("CLINIC_CURRENCY_CODE", "PHP")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

TEKNOCARE_MAKE_DEMO = (
    DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    and DATABASES["default"]["NAME"] == "teknocare_make_demo"
)
if TEKNOCARE_MAKE_DEMO:
    SESSION_COOKIE_NAME = "teknocare_make_session"
    CSRF_COOKIE_NAME = "teknocare_make_csrf"
