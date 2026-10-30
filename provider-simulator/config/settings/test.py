from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-only-secret-key"
ALLOWED_HOSTS = ["testserver"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Deterministic webhooks; tests enable duplicates and reordering explicitly.
WEBHOOK_DUPLICATE_RATE = 0.0
WEBHOOK_OUT_OF_ORDER_RATE = 0.0
