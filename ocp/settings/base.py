"""Settings for Open Conference Platform.

Every value can be set through an environment variable or a `.env` file in the
project root. See `.env.example` for the full list.
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]


def _load_dotenv(path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


if os.environ.get("DJANGO_SETTINGS_MODULE") != "ocp.settings.production":
    _load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


DEBUG = env_bool("OCP_DEBUG", False)

SECRET_KEY = env("OCP_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "change-me":
    if DEBUG:
        SECRET_KEY = "insecure-development-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("Set OCP_SECRET_KEY before running with OCP_DEBUG off.")

ALLOWED_HOSTS = env_list("OCP_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("OCP_CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "ocp.core",
    "ocp.reports",
    "ocp.accounts",
    "ocp.events",
    "ocp.ticketing",
    "ocp.checkin",
    "ocp.comms",
    "ocp.public",
    "ocp.organizer",
]

MIDDLEWARE = [
    "ocp.core.middleware.FrontendCorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ocp.urls"

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
                "ocp.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "ocp.wsgi.application"


def _database_config(url):
    if url.startswith("sqlite:"):
        path = url.split("sqlite:///", 1)[1] if "sqlite:///" in url else "db.sqlite3"
        name = Path(path) if os.path.isabs(path) else BASE_DIR / (path or "db.sqlite3")
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": name,
            "OPTIONS": {
                # IMMEDIATE takes the write lock when a transaction starts, so two
                # checkouts for the last ticket queue up instead of racing.
                "transaction_mode": "IMMEDIATE",
                "timeout": 20,
                "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
            },
            # A file (not in-memory) test database so concurrency tests can use threads.
            "TEST": {"NAME": BASE_DIR / "test_db.sqlite3"},
        }
    if url.startswith(("postgres:", "postgresql:")):
        parsed = urlparse(url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": parsed.port or 5432,
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {key: values[-1] for key, values in parse_qs(parsed.query).items()
                        if key in {"sslmode", "connect_timeout", "application_name"}},
        }
    raise ImproperlyConfigured("Unsupported OCP_DATABASE_URL scheme.")


DATABASES = {"default": _database_config(env("OCP_DATABASE_URL", "sqlite:///db.sqlite3"))}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "organizer:home"
LOGOUT_REDIRECT_URL = "login"

LANGUAGE_CODE = "en-nz"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = []
STATIC_ROOT = BASE_DIR / "staticfiles"

# Email: replaceable through configuration (COM-06).
EMAIL_BACKEND = env("OCP_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("OCP_DEFAULT_FROM_EMAIL", "Open Conference Platform <no-reply@localhost>")
EMAIL_HOST = env("OCP_EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("OCP_EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("OCP_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("OCP_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("OCP_EMAIL_USE_TLS", True)
EMAIL_TIMEOUT = 20

# Platform settings.
OCP_SITE_NAME = env("OCP_SITE_NAME", "Open Conference Platform")
OCP_BASE_URL = env("OCP_BASE_URL", "http://localhost:8000").rstrip("/")
OCP_PAYMENT_PROVIDER = env("OCP_PAYMENT_PROVIDER", "test")
OCP_STRIPE_SECRET_KEY = env("OCP_STRIPE_SECRET_KEY", "")
OCP_STRIPE_WEBHOOK_SECRET = env("OCP_STRIPE_WEBHOOK_SECRET", "")
OCP_GOOGLE_FONTS = env_bool("OCP_GOOGLE_FONTS", True)

# Security defaults for production. HTTPS is expected in front of the app.
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("OCP_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(env("OCP_HSTS_SECONDS", "0"))
    if env_bool("OCP_BEHIND_PROXY", False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "kv": {"format": "%(asctime)s level=%(levelname)s logger=%(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "kv"},
    },
    "loggers": {
        "ocp": {"handlers": ["console"], "level": env("OCP_LOG_LEVEL", "INFO"), "propagate": False},
        "django": {"handlers": ["console"], "level": "WARNING"},
    },
}

# Use sibling custom domains for reliable browser sessions (app.example.com and api.example.com).
OCP_FRONTEND_ORIGINS = env_list("OCP_FRONTEND_ORIGINS")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
                    if env_bool("OCP_MANIFEST_STATIC") else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
