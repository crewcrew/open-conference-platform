import os
import secrets
import subprocess
import sys
from io import StringIO
from unittest import TestCase

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings


class ProductionConfigTests(TestCase):
    def environment(self, **overrides):
        result = {k: v for k, v in os.environ.items() if not k.startswith(("OCP_", "DJANGO_"))}
        result.update({
            "DJANGO_SETTINGS_MODULE": "ocp.settings.production",
            "OCP_DEBUG": "0", "OCP_SECRET_KEY": secrets.token_urlsafe(64),
            "OCP_DATABASE_URL": "postgresql://ocp:unused@localhost/ocp?sslmode=require&connect_timeout=1",
            "OCP_ALLOWED_HOSTS": "api.example.com", "OCP_BASE_URL": "https://api.example.com",
            "OCP_FRONTEND_ORIGINS": "https://app.example.com",
            "OCP_CSRF_TRUSTED_ORIGINS": "https://app.example.com",
            "OCP_PAYMENT_PROVIDER": "stripe", "OCP_STRIPE_SECRET_KEY": "sk_test_unused",
            "OCP_STRIPE_WEBHOOK_SECRET": "whsec_unused",
            "OCP_EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OCP_EMAIL_HOST": "smtp.example.com", "OCP_DEFAULT_FROM_EMAIL": "tickets@example.com",
        })
        result.update(overrides)
        return result

    def import_settings(self, **overrides):
        return subprocess.run([sys.executable, "-c", "from django.conf import settings; print(settings.DEBUG)"],
                              env=self.environment(**overrides), capture_output=True, text=True, timeout=10)

    def test_valid_production_configuration_loads(self):
        result = self.import_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False")

    def test_unsafe_configurations_fail_closed(self):
        for override in [
            {"OCP_DEBUG": "1"}, {"OCP_SECRET_KEY": "short"},
            {"OCP_DATABASE_URL": "sqlite:///db.sqlite3"}, {"OCP_ALLOWED_HOSTS": "*"},
            {"OCP_BASE_URL": "http://api.example.com"}, {"OCP_BASE_URL": "https://api.example.com/path"},
            {"OCP_FRONTEND_ORIGINS": "https://app.example.com/path"}, {"OCP_CSRF_TRUSTED_ORIGINS": ""},
            {"OCP_PAYMENT_PROVIDER": "test"}, {"OCP_STRIPE_SECRET_KEY": ""},
            {"OCP_EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend"},
            {"OCP_SECURE_SSL_REDIRECT": "0"}, {"OCP_SESSION_COOKIE_SAMESITE": "invalid"},
        ]:
            with self.subTest(setting=next(iter(override))):
                result = self.import_settings(**override)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ImproperlyConfigured", result.stderr)

    def test_deployment_system_checks_have_no_errors(self):
        result = subprocess.run([sys.executable, "manage.py", "check", "--deploy", "--fail-level", "ERROR"],
                                env=self.environment(), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("security.W004", result.stderr)  # HSTS set
        self.assertNotIn("security.W008", result.stderr)  # HTTPS redirect set
        self.assertNotIn("security.W009", result.stderr)  # key strength
        self.assertNotIn("security.W012", result.stderr)  # secure session cookie
        self.assertNotIn("security.W016", result.stderr)  # secure CSRF cookie
        self.assertNotIn("security.W018", result.stderr)  # debug disabled

    @override_settings(DEBUG=False)
    def test_demo_seed_refuses_production(self):
        with self.assertRaisesRegex(CommandError, "local development"):
            call_command("seed_demo", stdout=StringIO())
