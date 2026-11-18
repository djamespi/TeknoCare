"""Local-only SQLite preview. Never reads .env or DATABASE_URL."""
import os
from pathlib import Path

from .settings_base import *


SECRET_KEY = "django-insecure-teknocare-local-development-only"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
local_database = Path(os.environ.get("TEKNOCARE_LOCAL_DB_PATH", "db.sqlite3"))
if not local_database.is_absolute():
    local_database = BASE_DIR / local_database
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": local_database}}
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
TEKNOCARE_LOCAL_DEMO = True
