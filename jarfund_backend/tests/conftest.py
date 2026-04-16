"""
pytest conftest — shared fixtures and database configuration.
"""
import django
from django.conf import settings


def pytest_configure():
    """Use SQLite for tests — faster and no PostgreSQL required."""
    if not settings.configured:
        settings.configure()

    # Override database to SQLite for speed
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME":   ":memory:",
    }

    # Disable Celery task execution during tests — tasks are mocked
    settings.CELERY_TASK_ALWAYS_EAGER = False
    settings.CELERY_TASK_EAGER_PROPAGATES = False

    # Use local memory cache for tests
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
