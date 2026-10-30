"""Provider simulator settings shared by every environment.

Connection URLs and credentials have no defaults: a missing one fails at startup.
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
    "simulator.core",
    "simulator.health",
    "simulator.messaging",
    "simulator.faults",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "simulator.faults.middleware.LatencyMiddleware",
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
    "DEFAULT_AUTHENTICATION_CLASSES": ["simulator.core.authentication.ApiKeyAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "simulator.core.errors.api_exception_handler",
}

# --- Celery ------------------------------------------------------------------
REDIS_URL = env("REDIS_URL")
CELERY_BROKER_URL = REDIS_URL
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE

# --- Provider behaviour ------------------------------------------------------
# Platform clients authenticate with this key (Authorization: Bearer <key>).
SIMULATOR_API_KEY = env("SIMULATOR_API_KEY")
# Shared with the platform, which verifies the HMAC signature on every webhook.
SIMULATOR_WEBHOOK_SECRET = env("SIMULATOR_WEBHOOK_SECRET")

# Each lifecycle step (accepted -> sent -> delivered -> read) waits a random delay in this range.
LIFECYCLE_MIN_DELAY_SECONDS = env.float("LIFECYCLE_MIN_DELAY_SECONDS", default=1.0)
LIFECYCLE_MAX_DELAY_SECONDS = env.float("LIFECYCLE_MAX_DELAY_SECONDS", default=4.0)

# Share of webhooks delivered twice, and share held back so they arrive after the next one.
WEBHOOK_DUPLICATE_RATE = env.float("WEBHOOK_DUPLICATE_RATE", default=0.1)
WEBHOOK_OUT_OF_ORDER_RATE = env.float("WEBHOOK_OUT_OF_ORDER_RATE", default=0.1)
WEBHOOK_OUT_OF_ORDER_DELAY_SECONDS = 10.0
WEBHOOK_TIMEOUT_SECONDS = 5.0
# A webhook the platform does not accept is retried with exponential backoff, then dropped.
WEBHOOK_MAX_RETRIES = 8
WEBHOOK_RETRY_MAX_DELAY_SECONDS = 60.0

# Test-number behaviour: the flaky number fails this many attempts per idempotency key,
# the rate-limited number throttles its first attempt with this Retry-After.
FLAKY_FAILED_ATTEMPTS = 2
RATE_LIMIT_RETRY_AFTER_SECONDS = 5

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
