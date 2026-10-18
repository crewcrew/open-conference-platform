"""Fail closed when essential production configuration is missing."""
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403


def require(condition, message):
    if not condition:
        raise ImproperlyConfigured(message)


require(not DEBUG, "Production requires OCP_DEBUG=0.")
require(len(SECRET_KEY) >= 50 and len(set(SECRET_KEY)) >= 8 and not SECRET_KEY.startswith("insecure"),
        "Production requires a random OCP_SECRET_KEY of at least 50 characters.")
require(DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql", "Production requires PostgreSQL.")
require(bool(ALLOWED_HOSTS) and "*" not in ALLOWED_HOSTS and all(h not in {"localhost", "127.0.0.1"} for h in ALLOWED_HOSTS),
        "Set explicit production OCP_ALLOWED_HOSTS.")
require(urlparse(OCP_BASE_URL).scheme == "https" and urlparse(OCP_BASE_URL).hostname in ALLOWED_HOSTS and
        not urlparse(OCP_BASE_URL).path and not urlparse(OCP_BASE_URL).query and
        not urlparse(OCP_BASE_URL).fragment and not urlparse(OCP_BASE_URL).username,
        "OCP_BASE_URL must be HTTPS on an allowed host.")
require(bool(OCP_FRONTEND_ORIGINS), "Set OCP_FRONTEND_ORIGINS to the exact Lovable/custom domain origin.")
for origin in OCP_FRONTEND_ORIGINS:
    parsed = urlparse(origin)
    require(parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and
            not parsed.password and not parsed.path and not parsed.query and not parsed.fragment,
            "Frontend origins must be exact HTTPS origins without a path.")
require(all(origin in CSRF_TRUSTED_ORIGINS for origin in OCP_FRONTEND_ORIGINS),
        "Add every frontend origin to OCP_CSRF_TRUSTED_ORIGINS.")
require(OCP_PAYMENT_PROVIDER == "stripe" and bool(OCP_STRIPE_SECRET_KEY) and bool(OCP_STRIPE_WEBHOOK_SECRET),
        "Configure Stripe keys and OCP_PAYMENT_PROVIDER=stripe for production.")
require(EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and bool(EMAIL_HOST),
        "Configure an SMTP email backend and host for production.")
require("@localhost" not in DEFAULT_FROM_EMAIL, "Set a verified production sender address.")
require(SECURE_SSL_REDIRECT, "Production requires HTTPS redirects.")
# Platform health probes reach the container over HTTP, before public TLS.
# Only these read-only status endpoints are exempt; login and API stay HTTPS.
SECURE_REDIRECT_EXEMPT = [r"^health/(live|ready)/$"]
SECURE_HSTS_SECONDS = int(env("OCP_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("OCP_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = False
# Prefer sibling custom domains so default Lax cookies remain same-site.
# None supports a lovable.app frontend, subject to browser third-party cookie restrictions.
SESSION_COOKIE_SAMESITE = env("OCP_SESSION_COOKIE_SAMESITE", "Lax")
require(SESSION_COOKIE_SAMESITE in {"Lax", "Strict", "None"}, "Invalid OCP_SESSION_COOKIE_SAMESITE.")
CSRF_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE

STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}
