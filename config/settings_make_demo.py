"""Connect to the dedicated Make sample database on the configured PostgreSQL host."""
from django.core.exceptions import ImproperlyConfigured

from .settings import *


if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("The Make demo requires its dedicated PostgreSQL database.")

DATABASES["default"]["NAME"] = "teknocare_make_demo"
TEKNOCARE_MAKE_DEMO = True
SESSION_COOKIE_NAME = "teknocare_make_session"
CSRF_COOKIE_NAME = "teknocare_make_csrf"
