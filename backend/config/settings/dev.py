from .base import *  # noqa

DEBUG = True

# Relax manifest static storage in dev (no collectstatic needed)
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
}
