from django.conf import settings
from django.contrib.staticfiles import finders


def portal_ready():
    return settings.TEKNOCARE_MAKE_PORTAL and bool(finders.find("portal/app.js") and finders.find("portal/style.css"))
