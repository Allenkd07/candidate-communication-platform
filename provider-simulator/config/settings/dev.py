from .base import *  # noqa: F403
from .base import SECRET_KEY

DEBUG = True
SECRET_KEY = SECRET_KEY or "dev-only-insecure-secret-key"
ALLOWED_HOSTS = ["*"]
