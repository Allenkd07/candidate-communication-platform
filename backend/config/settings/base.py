"""Settings shared by every environment.

Connection URLs have no defaults: a missing DATABASE_URL or REDIS_URL fails at startup.
See .env.example for the variables.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "candidate_comms.core",
    "candidate_comms.api",
    "candidate_comms.candidates",
    "candidate_comms.communications",
    "candidate_comms.integrations",
    "candidate_comms.webhooks",
    "candidate_comms.realtime",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": env.db("DATABASE_URL"),
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Django REST Framework ---------------------------------------------------
# Authentication and permissions are global defaults, so enabling auth needs no per-view changes.
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "candidate_comms.core.exceptions.handler.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Candidate Communication Platform API",
    "DESCRIPTION": "Manage candidates, send messages and track their delivery.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # One named enum per choice set, so generated frontend types share them.
    "ENUM_NAME_OVERRIDES": {
        "MessageStatusEnum": "candidate_comms.communications.models.MessageStatus",
        "ChannelEnum": "candidate_comms.communications.models.Channel",
    },
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "candidate_comms.api.schema.add_error_envelope",
    ],
}

# --- Celery ------------------------------------------------------------------
REDIS_URL = env("REDIS_URL")
CELERY_BROKER_URL = REDIS_URL
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "reconcile-stale-messages": {
        "task": "candidate_comms.communications.tasks.reconcile_stale_messages",
        "schedule": 60.0,
    },
}

# --- Candidates --------------------------------------------------------------
# Region assumed for phone numbers entered without a country code.
DEFAULT_PHONE_REGION = env("DEFAULT_PHONE_REGION", default="IN")

# --- Messaging ---------------------------------------------------------------
# Public base URL of this API; providers post delivery webhooks to
# {WEBHOOK_BASE_URL}/api/v1/webhooks/{gateway}/.
WEBHOOK_BASE_URL = env("WEBHOOK_BASE_URL")

SIMULATOR_API_URL = env("SIMULATOR_API_URL")
SIMULATOR_API_KEY = env("SIMULATOR_API_KEY")
SIMULATOR_WEBHOOK_SECRET = env("SIMULATOR_WEBHOOK_SECRET")
SIMULATOR_TIMEOUT_SECONDS = env.float("SIMULATOR_TIMEOUT_SECONDS", default=5.0)

# Gateway used for each channel when a send request does not name one.
MESSAGING_DEFAULT_GATEWAYS = {"sms": "simulator"}

# Automatic retries for transient gateway errors: exponential backoff with full jitter,
# capped per attempt. A Retry-After from the gateway takes precedence.
MESSAGE_SEND_MAX_RETRIES = 4
MESSAGE_RETRY_BASE_DELAY_SECONDS = 2.0
MESSAGE_RETRY_MAX_DELAY_SECONDS = 60.0

# Reconciliation: messages stuck in SENT longer than this are re-checked with the gateway
# (covers lost webhooks); messages stuck in QUEUED are re-enqueued (covers lost tasks).
RECONCILE_SENT_AFTER_SECONDS = 300
RECONCILE_QUEUED_AFTER_SECONDS = 600
RECONCILE_BATCH_SIZE = 100

# --- Realtime ----------------------------------------------------------------
REALTIME_CHANNEL = "ccp:events"
REALTIME_KEEPALIVE_SECONDS = 15.0

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
