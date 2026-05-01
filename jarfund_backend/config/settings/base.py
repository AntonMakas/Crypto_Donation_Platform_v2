"""
Base Django settings for JarFund.
All environment-specific files (local.py, production.py) inherit from this.
"""
import os
from pathlib import Path

import environ

# ─────────────────────────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialise django-environ
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))


# ─────────────────────────────────────────────────────────────────
#  SECURITY
# ─────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])


# ─────────────────────────────────────────────────────────────────
#  APPLICATIONS
# ─────────────────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
]

LOCAL_APPS = [
    "apps.users",
    "apps.jars",
    "apps.donations",
    "apps.blockchain",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ─────────────────────────────────────────────────────────────────
#  MIDDLEWARE
# ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",           # Must be before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ─────────────────────────────────────────────────────────────────
#  URL CONFIGURATION
# ─────────────────────────────────────────────────────────────────
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ─────────────────────────────────────────────────────────────────
#  TEMPLATES
# ─────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ─────────────────────────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────────────────────────
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://jarfund:jarfund_pass@localhost:5432/jarfund_db",
    )
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True  # Wrap each request in a transaction
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)


# ─────────────────────────────────────────────────────────────────
#  CACHE (Redis)
# ─────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,   # Degrade gracefully on Redis failure
        },
        "KEY_PREFIX": "jarfund",
    }
}


# ─────────────────────────────────────────────────────────────────
#  AUTHENTICATION
# ─────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ─────────────────────────────────────────────────────────────────
#  DJANGO REST FRAMEWORK
# ─────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",  # For browsable API
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "200/minute",
        # Custom scopes defined on sensitive views:
        "donate": "30/minute",
        "create_jar": "10/minute",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}


# ─────────────────────────────────────────────────────────────────
#  JWT SETTINGS
# ─────────────────────────────────────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}


# ─────────────────────────────────────────────────────────────────
#  CORS
# ─────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://jarfundfrontend-production.up.railway.app",
    ],
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-wallet-address",    # Custom header for wallet-based auth
    "x-wallet-signature",  # Signature header for wallet auth
]


# ─────────────────────────────────────────────────────────────────
#  CELERY (Async Tasks)
# ─────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 5          # 5 minutes max per task
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 4     # Soft limit: 4 minutes
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Broker connection retry — required in Celery 5.4+ to suppress deprecation
# warning and ensure the worker retries on startup if Redis is briefly unavailable.
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# Explicit queue configuration — ensures the worker binds to and consumes
# from the correct Redis queue rather than silently dropping tasks.
from kombu import Exchange, Queue

CELERY_DEFAULT_QUEUE = "celery"
CELERY_DEFAULT_EXCHANGE = "celery"
CELERY_DEFAULT_ROUTING_KEY = "celery"
CELERY_QUEUES = (
    Queue("celery", Exchange("celery"), routing_key="celery"),
)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1    # Fetch one task at a time; avoids starvation
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000 # Recycle workers to prevent memory leaks

# Task acknowledgment — mark tasks complete only after execution, not on receipt.
# Prevents task loss if the worker crashes mid-execution.
CELERY_TASK_ACKS_LATE = True

# Worker pool — explicitly use prefork to avoid hanging on startup in
# environments where the default pool detection may stall.
CELERY_WORKER_POOL = "prefork"



# Periodic task: verify pending donations every 30 seconds
CELERY_BEAT_SCHEDULE = {
    "verify-pending-donations": {
        "task": "apps.blockchain.tasks.verify_pending_donations",
        "schedule": 30.0,  # every 30 seconds
    },
    "update-jar-statuses": {
        "task": "apps.jars.tasks.update_expired_jar_statuses",
        "schedule": 60.0,  # every 60 seconds
    },
}


# ─────────────────────────────────────────────────────────────────
#  BLOCKCHAIN SETTINGS
# ─────────────────────────────────────────────────────────────────
BLOCKCHAIN = {
    "POLYGON_AMOY_RPC_URL": env(
        "POLYGON_AMOY_RPC_URL",
        default="https://rpc-amoy.polygon.technology",
    ),
    "POLYGON_MAINNET_RPC_URL": env(
        "POLYGON_MAINNET_RPC_URL",
        default="https://polygon-rpc.com",
    ),
    "CONTRACT_ADDRESS": env("CONTRACT_ADDRESS", default=""),
    "CHAIN_ID": env.int("CHAIN_ID", default=80002),  # Amoy = 80002
    "NETWORK_NAME": env("NETWORK_NAME", default="amoy"),
    # How many confirmations to wait before marking as verified
    "REQUIRED_CONFIRMATIONS": env.int("REQUIRED_CONFIRMATIONS", default=3),
    # Block explorer base URL
    "EXPLORER_URL": env(
        "EXPLORER_URL",
        default="https://amoy.polygonscan.com",
    ),
}

# Contract ABI is loaded from file at runtime
CONTRACT_ABI_PATH = BASE_DIR / "apps" / "blockchain" / "abi" / "JarFund.json"


# ─────────────────────────────────────────────────────────────────
#  DRF SPECTACULAR (OpenAPI docs)
# ─────────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "JarFund API",
    "DESCRIPTION": (
        "Secure Crypto Donation Platform with Transparency and Verification Mechanisms. "
        "Bachelor Thesis — KTU 2026. Anton Makasevych."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "auth",       "description": "Wallet-based authentication"},
        {"name": "jars",       "description": "Fundraising jar management"},
        {"name": "donations",  "description": "Donation operations"},
        {"name": "blockchain", "description": "On-chain verification"},
        {"name": "profile",    "description": "User profile"},
    ],
}


# ─────────────────────────────────────────────────────────────────
#  STATIC & MEDIA FILES
# ─────────────────────────────────────────────────────────────────
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ─────────────────────────────────────────────────────────────────
#  INTERNATIONALISATION
# ─────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_I18N      = True
USE_TZ        = True


# ─────────────────────────────────────────────────────────────────
#  DEFAULT AUTO FIELD
# ─────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ─────────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.blockchain": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
