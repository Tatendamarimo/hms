import os

from .base import *  # noqa

# CI provides DATABASE_URL pointing at Postgres; local test runs without one
# fall back to SQLite so the suite runs with zero infrastructure.
if not os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
    DATABASES["default"]["ATOMIC_REQUESTS"] = True

INSTALLED_APPS = [*INSTALLED_APPS, "apps.testapp"]  # noqa: F405 — concrete models for base-class tests

# No static file serving in tests
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405
STORAGES = {  # noqa: F405
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Lockout middleware exercises real request flows; disable rate limiting noise in tests
AXES_ENABLED = False

CELERY_TASK_ALWAYS_EAGER = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # noqa: S303 — speed, tests only

# Throttling off in tests
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}  # noqa: F405
