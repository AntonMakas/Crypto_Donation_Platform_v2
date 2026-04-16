"""
Production settings for JarFund.
Extends base.py with hardened security settings.
Deploy on: Railway, Render, Heroku, or any PaaS.
"""
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa: F401, F403

# ─────────────────────────────────────────────────────────────────
#  CORE
# ─────────────────────────────────────────────────────────────────
DEBUG = False

SECRET_KEY = env("SECRET_KEY")  # Must be set — no default in production

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


# ─────────────────────────────────────────────────────────────────
#  SECURITY HARDENING
# ─────────────────────────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER        = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT            = True
SESSION_COOKIE_SECURE          = True
CSRF_COOKIE_SECURE             = True
SECURE_BROWSER_XSS_FILTER      = True
SECURE_CONTENT_TYPE_NOSNIFF    = True
X_FRAME_OPTIONS                = "DENY"
SECURE_HSTS_SECONDS            = 31536000    # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD            = True
SECURE_REFERRER_POLICY         = "strict-origin-when-cross-origin"


# ─────────────────────────────────────────────────────────────────
#  CORS — only allow the actual frontend domain
# ─────────────────────────────────────────────────────────────────
# Get CORS origins from environment, with fallback to base defaults
_cors_origins = env.list("CORS_ALLOWED_ORIGINS", default=[])
if not _cors_origins:
    # Fallback to base.py defaults if env var is empty
    from .base import CORS_ALLOWED_ORIGINS as BASE_CORS
    _cors_origins = BASE_CORS
else:
    # Normalize: strip trailing slashes from each origin
    _cors_origins = [origin.rstrip('/') for origin in _cors_origins]

CORS_ALLOWED_ORIGINS = _cors_origins
CORS_ALLOW_ALL_ORIGINS = False


# ─────────────────────────────────────────────────────────────────
#  EMAIL
# ─────────────────────────────────────────────────────────────────
EMAIL_BACKEND      = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST         = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT         = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS      = True
EMAIL_HOST_USER    = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD= env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@jarfund.io")


# ─────────────────────────────────────────────────────────────────
#  SENTRY (Error Tracking)
# ─────────────────────────────────────────────────────────────────
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,   # 10% of transactions for performance
        send_default_pii=False,   # Privacy first — don't send PII to Sentry
        environment="production",
    )


# ─────────────────────────────────────────────────────────────────
#  THROTTLING — tighter in production
# ─────────────────────────────────────────────────────────────────
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "30/minute",
    "user": "120/minute",
    "donate": "10/minute",
    "create_jar": "5/minute",
}


# ─────────────────────────────────────────────────────────────────
#  ADMIN URL — obscure in production
# ─────────────────────────────────────────────────────────────────
ADMIN_URL = env("ADMIN_URL", default="admin-jarfund-secure/")


# ─────────────────────────────────────────────────────────────────
#  LOGGING — structured for log aggregators
# ─────────────────────────────────────────────────────────────────
LOGGING["root"]["level"] = "WARNING"  # noqa: F405
