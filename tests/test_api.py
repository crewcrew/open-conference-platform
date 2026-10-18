import json
from unittest.mock import patch

from django.db import OperationalError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.template.loader import get_template
from django.contrib.staticfiles import finders

from ocp.accounts.models import Membership, Role
from ocp.events.models import Event, TicketType
from .helpers import make_event, buy


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", OCP_PAYMENT_PROVIDER="test")
class ApiTests(TestCase):
    def setUp(self):
        self.setup = make_event()
        self.event = self.setup["event"]
        self.prefix = f"/api/v1/organizations/{self.setup['org'].slug}/events/{self.event.pk}/"

    def test_public_api_excludes_drafts_unlisted_and_ticket_secrets(self):
        path = f"/api/v1/events/{self.event.slug}/"
        data = self.client.get(path).json()
        self.assertTrue(data["ticket_types"])
        for ticket in data["ticket_types"]:
            self.assertNotIn("access_code", ticket)
        self.assertNotIn("online_url", data)
        self.event.visibility = Event.Visibility.UNLISTED
        self.event.save()
        self.assertEqual(self.client.get("/api/v1/events/").json()["results"], [])
        self.assertEqual(self.client.get(path).status_code, 200)
        self.event.status = Event.Status.DRAFT
        self.event.save()
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_authentication_csrf_and_rotated_session(self):
        client = Client(enforce_csrf_checks=True)
        self.setup["owner"].set_password("a-long-test-password")
        self.setup["owner"].save()
        token = client.get("/api/v1/session/").json()["csrf_token"]
        payload = json.dumps({"email": self.setup["owner"].username, "password": "a-long-test-password"})
        self.assertEqual(client.post("/api/v1/auth/login/", payload, content_type="application/json").status_code, 403)
        response = client.post("/api/v1/auth/login/", payload, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(len(response.json()["organizations"]), 1)
        new_token = response.json()["csrf_token"]
        self.assertEqual(client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=new_token).status_code, 200)
        self.assertFalse(client.get("/api/v1/session/").json()["authenticated"])

    def test_malformed_login_is_rejected(self):
        for payload in ['[]', 'null', '{', '{"email": [], "password": 1}']:
            self.assertEqual(self.client.post("/api/v1/auth/login/", payload, content_type="application/json").status_code, 400)

    def test_api_membership_and_capabilities(self):
        self.assertEqual(self.client.get(self.prefix + "orders/").status_code, 401)
        self.client.force_login(self.setup["owner"])
        self.assertEqual(self.client.get(self.prefix + "dashboard/").status_code, 200)
        member = Membership.objects.get(user=self.setup["owner"], organization=self.setup["org"])
        member.role = Role.VOLUNTEER
        member.save()
        member.events.add(self.event)
        response = self.client.get(f"/api/v1/organizations/{self.setup['org'].slug}/events/").json()
        self.assertEqual(response["results"][0]["capabilities"], ["check_in"])
        for suffix in ["orders/", "attendees/", "dashboard/", "communications/"]:
            self.assertEqual(self.client.get(self.prefix + suffix).status_code, 403)
        member.events.clear()
        self.assertEqual(self.client.get(f"/api/v1/organizations/{self.setup['org'].slug}/events/").json()["results"], [])
        member.delete()
        self.assertEqual(self.client.get(self.prefix + "orders/").status_code, 404)

    def test_organizer_data_and_search_do_not_return_access_tokens(self):
        order = buy(self.setup, {"free": 1}, email="private@example.com")
        self.client.force_login(self.setup["owner"])
        response = self.client.get(self.prefix + "orders/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertNotContains(response, order.access_token)
        self.assertEqual(self.client.get(self.prefix + "attendees/?q=private").json()["count"], 1)
        self.assertEqual(self.client.get(self.prefix + "attendees/?q=nobody").json()["count"], 0)
        self.assertEqual(self.client.get(self.prefix + "orders/?page=wrong").status_code, 400)
        self.assertEqual(self.client.get(self.prefix + "communications/").status_code, 200)

    @override_settings(OCP_FRONTEND_ORIGINS=["https://app.example.com"])
    def test_cors_exact_origin_and_private_cache_policy(self):
        path = "/api/v1/session/"
        response = self.client.get(path, HTTP_ORIGIN="https://app.example.com")
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://app.example.com")
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.options(path, HTTP_ORIGIN="https://app.example.com").status_code, 204)
        denied = self.client.get(path, HTTP_ORIGIN="https://app.example.com.attacker.invalid")
        self.assertNotIn("Access-Control-Allow-Origin", denied)
        self.assertEqual(self.client.options(path, HTTP_ORIGIN="https://evil.invalid").status_code, 403)

    def test_health(self):
        self.assertEqual(self.client.get("/health/live/").status_code, 200)
        self.assertEqual(self.client.get("/health/ready/").status_code, 200)
        with patch("ocp.core.health.connection.cursor", side_effect=OperationalError("private connection details")):
            response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "private connection", status_code=503)

    def test_feature_owned_assets_and_templates(self):
        for name in ["base.html", "registration/login.html", "organizer/dashboard.html", "public/event.html", "checkin/scanner.html", "emails/confirmation.txt"]:
            self.assertIsNotNone(get_template(name))
        self.assertIsNotNone(finders.find("core/app.css"))
        self.assertIsNotNone(finders.find("checkin/scanner.js"))

    def test_management_pages_still_render_after_feature_move(self):
        self.client.force_login(self.setup["owner"])
        prefix = f"/manage/{self.setup['org'].slug}/e/{self.event.pk}/"
        for suffix in ["", "edit/", "sessions/", "tickets/", "questions/", "coupons/", "orders/", "attendees/", "emails/", "emails/new/", "reports/", "history/"]:
            with self.subTest(page=suffix):
                self.assertEqual(self.client.get(prefix + suffix).status_code, 200)
        for suffix in ["", "settings/", "team/"]:
            with self.subTest(organization_page=suffix):
                self.assertEqual(self.client.get(f"/manage/{self.setup['org'].slug}/" + suffix).status_code, 200)
