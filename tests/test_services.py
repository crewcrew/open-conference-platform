import hashlib
import hmac
import json
import time
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone

from ocp.comms.models import Communication, Delivery, Unsubscribe
from ocp.comms.services import process_due, recipients, unsubscribe_token
from ocp.events.formatting import compact_range, date_range
from ocp.ticketing.models import Order
from ocp.ticketing.payments import StripeProvider, to_minor_units, verify_stripe_signature

from .helpers import buy, make_event

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


class StripeSignatureTests(TestCase):
    def sign(self, payload, secret, timestamp):
        signature = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={signature}"

    def test_valid_signature_passes_and_tampering_fails(self):
        payload = b'{"id": "evt_1"}'
        now = int(time.time())
        header = self.sign(payload, "whsec_test", now)
        self.assertTrue(verify_stripe_signature(payload, header, "whsec_test", now=now))
        self.assertFalse(verify_stripe_signature(payload + b" ", header, "whsec_test", now=now))
        self.assertFalse(verify_stripe_signature(payload, header, "whsec_other", now=now))
        self.assertFalse(verify_stripe_signature(payload, header, "whsec_test", now=now + 3600))

    def test_completed_session_becomes_a_paid_event(self):
        provider = StripeProvider("sk_test_x", "whsec_test")
        body = json.dumps({
            "id": "evt_2", "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_1", "payment_status": "paid", "amount_total": 80400, "currency": "nzd", "payment_intent": "pi_1"}},
        }).encode()
        request = RequestFactory().post("/payments/webhook/stripe/", data=body, content_type="application/json",
                                        HTTP_STRIPE_SIGNATURE=self.sign(body, "whsec_test", int(time.time())))
        [event] = provider.parse_webhook(request)
        self.assertEqual((event.kind, event.payment_ref, event.amount, event.payment_intent), ("paid", "cs_1", Decimal("804.00"), "pi_1"))

    def test_minor_units(self):
        self.assertEqual(to_minor_units(Decimal("804.00"), "NZD"), 80400)
        self.assertEqual(to_minor_units(Decimal("1500"), "JPY"), 1500)


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class CommunicationTests(TestCase):
    def test_marketing_only_reaches_opted_in_and_respects_unsubscribe(self):
        setup = make_event()
        buy(setup, {"free": 1}, email="yes@example.com", consent=True)
        buy(setup, {"free": 1}, email="no@example.com", consent=False)
        buy(setup, {"free": 1}, email="gone@example.com", consent=True)
        Unsubscribe.objects.create(organization=setup["org"], email="gone@example.com")
        draft = Communication(event=setup["event"], kind="marketing", subject="News", body="Hi {first name}", audience={})
        self.assertEqual([email for email, _, _ in recipients(draft)], ["yes@example.com"])
        update = Communication(event=setup["event"], kind="update", subject="Room change", body="Hi", audience={})
        self.assertEqual(len(recipients(update)), 3)

    def test_update_filtered_by_session_and_scheduled_send_happens_once(self):
        setup = make_event()
        buy(setup, {"standard": 1}, email="a@example.com", sessions=[setup["workshop_a"].pk])
        buy(setup, {"standard": 1}, email="b@example.com", sessions=[setup["workshop_b"].pk])
        mail.outbox.clear()
        comm = Communication.objects.create(
            event=setup["event"], kind="update", subject="Workshop A moved", body="Hi {first name}, {workshop} moved. {booking link}",
            audience={"session": setup["workshop_a"].pk}, status=Communication.Status.SCHEDULED,
            scheduled_for=timezone.now() - timedelta(minutes=1),
        )
        self.assertEqual(process_due(), 1)
        self.assertEqual(process_due(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["a@example.com"])
        self.assertIn("Workshop A moved", mail.outbox[0].body)
        self.assertIn("/booking/", mail.outbox[0].body)
        comm.refresh_from_db()
        self.assertEqual(comm.recipient_count, 1)

    def test_unsubscribe_link(self):
        setup = make_event()
        token = unsubscribe_token(setup["org"], "Someone@Example.com")
        Client().post(f"/unsubscribe/{token}/")
        self.assertTrue(Unsubscribe.objects.filter(organization=setup["org"], email="someone@example.com").exists())

    def test_booking_lookup_sends_links_without_revealing_bookings(self):
        setup = make_event()
        order = buy(setup, {"free": 1}, email="me@example.com")
        mail.outbox.clear()
        client = Client()
        known = client.post("/booking/", {"email": "me@example.com"}, follow=True)
        unknown = client.post("/booking/", {"email": "nobody@example.com"}, follow=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(order.access_token, mail.outbox[0].body)
        self.assertEqual(
            [str(m) for m in known.context["messages"]], [str(m) for m in unknown.context["messages"]]
        )


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class PublicFlowTests(TestCase):
    def test_event_page_to_booking_through_the_browser_flow(self):
        setup = make_event()
        client = Client()
        page = client.get(f"/e/{setup['event'].slug}/")
        self.assertContains(page, "All times NZ")  # NZST or NZDT, shown with the UTC offset
        response = client.post(f"/e/{setup['event'].slug}/", {f"qty_{setup['standard'].pk}": "1"})
        order = Order.objects.get()
        self.assertRedirects(response, f"/checkout/{order.access_token}/", fetch_redirect_response=False)
        attendee = order.attendees.get()
        form = {
            "action": "pay",
            "p-first_name": "Ada", "p-last_name": "Lovelace", "p-email": "ada@example.com",
            f"a{attendee.pk}-is_purchaser": "on",
            f"a{attendee.pk}-group_workshop": str(setup["workshop_a"].pk),
        }
        response = client.post(f"/checkout/{order.access_token}/", form)
        order.refresh_from_db()
        self.assertTrue(response["Location"].startswith("/pay/test/"))
        with self.captureOnCommitCallbacks(execute=True):
            client.post(response["Location"], {"action": "pay"})
        booking = client.get(f"/booking/{order.access_token}/")
        self.assertContains(booking, "You're in, Ada.")
        self.assertContains(booking, 'class="qr"', count=1)
        self.assertEqual(order.attendees.get().full_name, "Ada Lovelace")

    def test_checkout_shows_errors_and_keeps_typed_values(self):
        setup = make_event()
        client = Client()
        client.post(f"/e/{setup['event'].slug}/", {f"qty_{setup['standard'].pk}": "1"})
        order = Order.objects.get()
        response = client.post(f"/checkout/{order.access_token}/", {"action": "pay", "p-first_name": "Ada"})
        self.assertContains(response, "Some details need fixing")
        self.assertContains(response, 'value="Ada"')
        response = client.post(f"/checkout/{order.access_token}/", {"action": "apply_coupon", "coupon_code": "save20", "p-first_name": "Ada"})
        self.assertContains(response, "SAVE20")
        self.assertContains(response, 'value="Ada"')
        order.refresh_from_db()
        self.assertEqual(order.discount_total, Decimal("99.00"))

    def test_draft_events_are_hidden_from_the_public(self):
        setup = make_event()
        setup["event"].status = "draft"
        setup["event"].save()
        self.assertEqual(Client().get(f"/e/{setup['event'].slug}/").status_code, 404)
        client = Client()
        client.force_login(setup["owner"])
        self.assertContains(client.get(f"/e/{setup['event'].slug}/"), "Preview")


class FormattingTests(TestCase):
    def test_date_ranges(self):
        from datetime import datetime

        start, end = datetime(2027, 3, 18, 8), datetime(2027, 3, 19, 17)
        self.assertEqual(date_range(start, end), "Thu 18 – Fri 19 March 2027")
        self.assertEqual(compact_range(start, end), "18–19 Mar 2027")


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class RetentionTests(TestCase):
    def test_purge_removes_personal_data_after_retention(self):
        setup = make_event()
        order = buy(setup, {"free": 1}, email="private@example.com")
        event = setup["event"]
        event.retention_days = 30
        event.ends_at = timezone.now() - timedelta(days=31)
        event.starts_at = event.ends_at - timedelta(days=1)
        event.save()
        call_command("purge_personal_data", stdout=mock.MagicMock())
        order.refresh_from_db()
        self.assertEqual(order.purchaser_email, "")
        self.assertEqual(order.attendees.get().email, "")
        self.assertEqual(order.total, Decimal("0.00"))
        self.assertFalse(Delivery.objects.filter(to_email="private@example.com").exists())
