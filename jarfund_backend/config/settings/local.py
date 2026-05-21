"""
Local development settings for JarFund.
Extends base.py with dev-friendly overrides.
"""
from .base import *  # noqa: F401, F403

#  CORE OVERRIDES
DEBUG = True

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-dev-key-change-this-in-production-jarfund-2026",
)

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "*"]


#  DEV TOOLS
INSTALLED_APPS += [  # noqa: F405
    "django_extensions",
]


#  CORS — allow all in dev
CORS_ALLOW_ALL_ORIGINS = True

#  CACHING — use local memory in dev (no Redis required)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

#  THROTTLING — disable in dev for easier testing
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

#  LOGGING — verbose in dev
LOGGING["root"]["level"] = "DEBUG"  # noqa: F405
LOGGING["loggers"]["apps.blockchain"]["level"] = "DEBUG"  # noqa: F405
