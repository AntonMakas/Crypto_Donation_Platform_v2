"""
Local development settings for JarFund.
Extends base.py with dev-friendly overrides.
"""
from .base import *  # noqa: F401, F403

# ─────────────────────────────────────────────────────────────────
#  CORE OVERRIDES
# ─────────────────────────────────────────────────────────────────
DEBUG = True

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-dev-key-change-this-in-production-jarfund-2026",
)

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "*"]


# ─────────────────────────────────────────────────────────────────
#  DEV TOOLS
# ─────────────────────────────────────────────────────────────────
INSTALLED_APPS += [  # noqa: F405
    "django_extensions",
]


# ─────────────────────────────────────────────────────────────────
#  DATABASE (SQLite fallback for quick local start)
# ─────────────────────────────────────────────────────────────────
# Comment this block out when using PostgreSQL locally
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }


# ─────────────────────────────────────────────────────────────────
#  CORS — allow all in dev
# ─────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True


# ─────────────────────────────────────────────────────────────────
#  EMAIL — print to console in dev
# ─────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# ─────────────────────────────────────────────────────────────────
#  CACHING — use local memory in dev (no Redis required)
# ─────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


# ─────────────────────────────────────────────────────────────────
#  THROTTLING — disable in dev for easier testing
# ─────────────────────────────────────────────────────────────────
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405


# ─────────────────────────────────────────────────────────────────
#  LOGGING — verbose in dev
# ─────────────────────────────────────────────────────────────────
LOGGING["root"]["level"] = "DEBUG"  # noqa: F405
LOGGING["loggers"]["apps.blockchain"]["level"] = "DEBUG"  # noqa: F405
