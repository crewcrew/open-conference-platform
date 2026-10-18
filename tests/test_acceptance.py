"""The ten pilot acceptance scenarios from PRD section 11, plus the edge cases around them."""

import csv
import io
import threading
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from ocp.accounts.models import Organization, Role
from ocp.checkin.models import CheckInEvent
from ocp.checkin.services import check_in
from ocp.comms.models import Delivery
from ocp.events.models import Session, TicketType
from ocp.ticketing import checkout
from ocp.ticketing.checkout import CheckoutError
from ocp.ticketing.models import Order, Redemption, Refund, Ticket
from ocp.ticketing.payments import ProviderEvent, process_provider_event
from ocp.ticketing.refunds import RefundError, cancel_and_refund

from .helpers import buy, fill_details, make_event, make_user

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class Scenario1FreeRegistration(TestCase):
    def test_free_registration_creates_one_of_each_and_emails(self):
        setup = make_event()
        with self.captureOnCommitCallbacks(execute=True):
            order = buy(setup, {"free": 1})
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.total, Decimal("0.00"))
        self.assertEqual(order.attendees.count(), 1)
        self.assertEqual(order.tickets.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(order.tickets.get().display_id, mail.outbox[0].body)
        self.assertIn("help@example.com", mail.outbox[0].body)  # COM-04 support contact


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class Scenario2PaidRegistration(TestCase):
    def test_pending_until_verified_payment_then_tickets_issued_once(self):
        setup = make_event()
        order = buy(setup, {"standard": 2}, pay=False)
        url = checkout.begin_payment(order, success_url="/done/", cancel_url="/back/")
        order.refresh_from_db()
        self.assertTrue(url.startswith("/pay/test/"))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.tickets.count(), 0)

        client = Client()
        with self.captureOnCommitCallbacks(execute=True):
            response = client.post(url, {"action": "pay"})
        self.assertRedirects(response, f"/booking/{order.access_token}/", fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.tickets.count(), 2)

        # The provider repeating its callback, or a second confirm, doesn't issue more tickets.
        process_provider_event("test", ProviderEvent(event_id=f"{order.payment_ref}:paid", kind="paid", payment_ref=order.payment_ref, amount=order.total))
        checkout.confirm_paid(order.pk, provider="test", payment_ref=order.payment_ref)
        self.assertEqual(Ticket.objects.filter(order=order).count(), 2)
        self.assertEqual(Delivery.objects.filter(order=order, kind=Delivery.Kind.CONFIRMATION).count(), 1)

    def test_declined_payment_releases_places(self):
        setup = make_event()
        order = buy(setup, {"standard": 2}, pay=False)
        url = checkout.begin_payment(order, success_url="/done/", cancel_url="/back/")
        Client().post(url, {"action": "decline"})
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.FAILED)
        self.assertEqual(TicketType.objects.get(pk=setup["standard"].pk).reserved, 0)
        self.assertEqual(Session.objects.get(pk=setup["workshop_a"].pk).reserved, 0)

    def test_wrong_amount_is_not_accepted(self):
        setup = make_event()
        order = buy(setup, {"standard": 1}, pay=False)
        checkout.begin_payment(order, success_url="/done/", cancel_url="/back/")
        order.refresh_from_db()
        process_provider_event("test", ProviderEvent(event_id="x", kind="paid", payment_ref=order.payment_ref, amount=Decimal("1.00")))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.FAILED)
        self.assertEqual(order.tickets.count(), 0)

    def test_test_payment_page_is_off_unless_test_provider(self):
        setup = make_event()
        order = buy(setup, {"standard": 1}, pay=False)
        url = checkout.begin_payment(order, success_url="/done/", cancel_url="/back/")
        with override_settings(OCP_PAYMENT_PROVIDER="stripe"):
            self.assertEqual(Client().post(url, {"action": "pay"}).status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class Scenario3LastTicket(TransactionTestCase):
    def test_two_simultaneous_attempts_for_the_last_ticket(self):
        setup = make_event(quantity=1)
        event, standard = setup["event"], setup["standard"]
        barrier = threading.Barrier(2)
        outcomes = []

        def attempt():
            try:
                barrier.wait()
                checkout.start_order(event, {standard.pk: 1})
                outcomes.append("ok")
            except CheckoutError:
                outcomes.append("sold out")
            finally:
                connection.close()

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(outcomes), ["ok", "sold out"])
        self.assertEqual(TicketType.objects.get(pk=standard.pk).reserved, 1)

    def test_capacity_counts_holds_and_returns_on_expiry(self):
        setup = make_event(quantity=2)
        first = checkout.start_order(setup["event"], {setup["standard"].pk: 2})
        with self.assertRaises(CheckoutError):
            checkout.start_order(setup["event"], {setup["standard"].pk: 1})
        Order.objects.filter(pk=first.pk).update(hold_expires_at=timezone.now() - timedelta(minutes=1))
        second = checkout.start_order(setup["event"], {setup["standard"].pk: 1})
        first.refresh_from_db()
        self.assertEqual(first.status, Order.Status.EXPIRED)
        self.assertEqual(second.status, Order.Status.PENDING)
        self.assertEqual(TicketType.objects.get(pk=setup["standard"].pk).reserved, 1)

    def test_payment_after_expiry_with_no_places_left_is_refunded(self):
        setup = make_event(quantity=1)
        late = buy(setup, {"free": 0, "student": 1}, pay=False)
        checkout.begin_payment(late, success_url="/d/", cancel_url="/b/")
        late.refresh_from_db()
        Order.objects.filter(pk=late.pk).update(hold_expires_at=timezone.now() - timedelta(minutes=1))
        buy(setup, {"student": 1})  # releases the expired hold and takes the last place
        process_provider_event("test", ProviderEvent(event_id="late", kind="paid", payment_ref=late.payment_ref, amount=late.total))
        late.refresh_from_db()
        self.assertEqual(late.status, Order.Status.FAILED)
        self.assertEqual(late.tickets.count(), 0)
        self.assertEqual(Refund.objects.get(order=late).amount, late.total)


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class Scenario4Coupons(TestCase):
    def setUp(self):
        self.setup = make_event()

    def test_valid_coupon_changes_total_and_is_recorded(self):
        order = buy(self.setup, {"standard": 2}, coupon="save20")
        # 2 × 495 = 990, minus 20% = 792, plus 2 × 6.00 booking fee = 804, GST included 104.87.
        self.assertEqual(order.discount_total, Decimal("198.00"))
        self.assertEqual(order.total, Decimal("804.00"))
        self.assertEqual(order.tax_total, Decimal("104.87"))
        self.assertEqual(Redemption.objects.get(order=order).discount_amount, Decimal("198.00"))

    def test_expired_coupon_is_rejected_with_a_clear_message(self):
        coupon = self.setup["coupon"]
        coupon.ends_at = timezone.now() - timedelta(days=1)
        coupon.save()
        order = checkout.start_order(self.setup["event"], {self.setup["standard"].pk: 1})
        with self.assertRaisesMessage(CheckoutError, "ended on"):
            checkout.apply_coupon(order, "SAVE20")

    def test_exhausted_disabled_and_ineligible_coupons(self):
        coupon = self.setup["coupon"]
        coupon.max_redemptions = 1
        coupon.save()
        buy(self.setup, {"standard": 1}, coupon="SAVE20")
        order = checkout.start_order(self.setup["event"], {self.setup["standard"].pk: 1})
        with self.assertRaisesMessage(CheckoutError, "used up"):
            checkout.apply_coupon(order, "SAVE20")
        coupon.is_active = False
        coupon.save()
        with self.assertRaisesMessage(CheckoutError, "can't be used"):
            checkout.apply_coupon(order, "SAVE20")
        coupon.is_active = True
        coupon.max_redemptions = None
        coupon.save()
        student_order = checkout.start_order(self.setup["event"], {self.setup["student"].pk: 1})
        with self.assertRaisesMessage(CheckoutError, "only applies to Standard"):
            checkout.apply_coupon(student_order, "SAVE20")

    def test_abandoned_checkout_gives_the_coupon_use_back(self):
        coupon = self.setup["coupon"]
        coupon.max_redemptions = 1
        coupon.save()
        order = checkout.start_order(self.setup["event"], {self.setup["standard"].pk: 1})
        checkout.apply_coupon(order, "SAVE20")
        checkout.cancel_checkout(order)
        other = checkout.start_order(self.setup["event"], {self.setup["standard"].pk: 1})
        checkout.apply_coupon(other, "SAVE20")  # doesn't raise


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class Scenario5GroupOrder(TestCase):
    def test_group_order_has_a_distinct_attendee_and_ticket_each(self):
        setup = make_event()
        with self.captureOnCommitCallbacks(execute=True):
            order = buy(setup, {"standard": 3}, sessions=[setup["workshop_a"].pk, setup["workshop_a"].pk, setup["workshop_b"].pk])
        tickets = list(order.tickets.select_related("attendee"))
        self.assertEqual(len(tickets), 3)
        self.assertEqual(len({t.attendee_id for t in tickets}), 3)
        self.assertEqual(len({t.code for t in tickets}), 3)
        self.assertGreaterEqual(len(tickets[0].code), 24)  # non-guessable
        # Purchaser gets everything; the two other attendees get their own ticket.
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ["buyer@example.com", "person1@example.com", "person2@example.com"])

    def test_full_session_cannot_be_chosen(self):
        setup = make_event(workshop_capacity=1)
        buy(setup, {"standard": 1}, sessions=[setup["workshop_a"].pk])
        order = checkout.start_order(setup["event"], {setup["standard"].pk: 1})
        with self.assertRaisesMessage(CheckoutError, "filled up"):
            fill_details(order, sessions=[setup["workshop_a"].pk])


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class Scenario6Refunds(TestCase):
    def test_refund_updates_order_ticket_and_reports(self):
        setup = make_event()
        order = buy(setup, {"standard": 2})
        ticket = order.tickets.first()
        cancel_and_refund(order, [ticket], Decimal("247.50"), setup["owner"], note="Within policy")
        order.refresh_from_db()
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.CANCELLED)
        self.assertEqual(order.status, Order.Status.PARTIALLY_REFUNDED)
        self.assertEqual(order.refunded_total, Decimal("247.50"))
        self.assertEqual(Refund.objects.get(order=order).status, Refund.Status.SUCCEEDED)
        self.assertEqual(TicketType.objects.get(pk=setup["standard"].pk).reserved, 1)
        self.assertTrue(setup["event"].audit_logs.filter(action="order.refund").exists())

        client = Client()
        client.force_login(setup["owner"])
        report = client.get(f"/manage/{setup['org'].slug}/e/{setup['event'].pk}/reports/")
        self.assertContains(report, "247.50")

    def test_full_refund_of_every_ticket_marks_order_refunded(self):
        setup = make_event()
        order = buy(setup, {"standard": 1})
        cancel_and_refund(order, list(order.tickets.all()), order.total, setup["owner"])
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REFUNDED)

    def test_cannot_refund_more_than_was_paid_or_cancel_twice(self):
        setup = make_event()
        order = buy(setup, {"standard": 1})
        ticket = order.tickets.get()
        with self.assertRaises(RefundError):
            cancel_and_refund(order, [ticket], order.total + 1, setup["owner"])
        cancel_and_refund(order, [ticket], Decimal("0"), setup["owner"])
        with self.assertRaises(RefundError):
            cancel_and_refund(order, [Ticket.objects.get(pk=ticket.pk)], Decimal("0"), setup["owner"])

    def test_refund_flow_through_the_order_page(self):
        setup = make_event()
        order = buy(setup, {"standard": 2})
        ticket = order.tickets.first()
        client = Client()
        client.force_login(setup["owner"])
        url = f"/manage/{setup['org'].slug}/e/{setup['event'].pk}/orders/{order.pk}/"
        review = client.post(url, {"action": "review", "tickets": [ticket.pk], "amount_choice": "full", "notify": "on"})
        self.assertContains(review, "Refund NZD 495.00 and cancel 1 ticket?")
        self.assertEqual(Ticket.objects.get(pk=ticket.pk).status, Ticket.Status.VALID)  # nothing happens until confirmed
        client.post(url, {"action": "confirm", "tickets": [ticket.pk], "amount_choice": "custom", "custom_amount": "495.00", "notify": "on"})
        self.assertEqual(Ticket.objects.get(pk=ticket.pk).status, Ticket.Status.CANCELLED)


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class Scenario7CheckIn(TestCase):
    def test_first_scan_admits_second_reports_already_checked_in(self):
        setup = make_event()
        order = buy(setup, {"standard": 2})
        ticket = order.tickets.first()
        volunteer = make_user("vol@example.com", Role.VOLUNTEER, setup["org"])
        first = check_in(setup["event"], volunteer, code=ticket.code, lane="Lane 1", device_id="phone-1")
        second = check_in(setup["event"], volunteer, code=ticket.code, lane="Lane 2")
        self.assertEqual(first.result, CheckInEvent.Result.ADMITTED)
        self.assertEqual(second.result, CheckInEvent.Result.DUPLICATE)
        self.assertEqual(CheckInEvent.objects.filter(ticket=ticket, result=CheckInEvent.Result.ADMITTED).count(), 1)
        self.assertEqual(first.actor, volunteer)
        self.assertEqual(first.device_id, "phone-1")

    def test_cancelled_and_unknown_tickets_are_rejected(self):
        setup = make_event()
        order = buy(setup, {"standard": 1})
        ticket = order.tickets.get()
        cancel_and_refund(order, [ticket], Decimal("100"), setup["owner"])
        refunded = check_in(setup["event"], setup["owner"], code=ticket.code)
        unknown = check_in(setup["event"], setup["owner"], code="not-a-ticket")
        self.assertEqual(refunded.result, CheckInEvent.Result.INVALID)
        self.assertIn("refunded", refunded.reason)
        self.assertEqual(unknown.result, CheckInEvent.Result.INVALID)

    def test_offline_scans_sync_once(self):
        setup = make_event()
        order = buy(setup, {"standard": 1})
        ticket = order.tickets.get()
        client = Client()
        client.force_login(setup["owner"])
        payload = {"scans": [{"code": ticket.code, "client_scan_id": "abc-1", "scanned_at": timezone.now().isoformat(), "offline": True}]}
        url = f"/checkin/{setup['event'].pk}/scan/"
        first = client.post(url, payload, content_type="application/json").json()
        again = client.post(url, payload, content_type="application/json").json()
        self.assertEqual(first["results"][0]["result"], "admitted")
        self.assertEqual(again["results"][0]["result"], "admitted")
        self.assertEqual(CheckInEvent.objects.filter(client_scan_id="abc-1").count(), 1)
        self.assertTrue(CheckInEvent.objects.get(client_scan_id="abc-1").was_offline)


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class Scenario8Permissions(TestCase):
    def test_volunteer_cannot_reach_other_organizations_or_events(self):
        setup = make_event("one")
        other = make_event("two")
        volunteer = make_user("vol@example.com", Role.VOLUNTEER, setup["org"])
        volunteer.memberships.get().events.add(setup["event"])
        unassigned = setup["org"].events.create(
            name="Other", slug="other", starts_at=setup["event"].starts_at, ends_at=setup["event"].ends_at,
            contact_email="x@example.com", venue_name="Hall",
        )
        client = Client()
        client.force_login(volunteer)
        self.assertEqual(client.get(f"/checkin/{setup['event'].pk}/").status_code, 200)
        self.assertEqual(client.get(f"/checkin/{unassigned.pk}/").status_code, 403)
        self.assertEqual(client.get(f"/checkin/{other['event'].pk}/").status_code, 404)
        self.assertEqual(client.get(f"/manage/{other['org'].slug}/").status_code, 404)
        self.assertEqual(client.get(f"/manage/{setup['org'].slug}/e/{setup['event'].pk}/attendees/").status_code, 403)
        self.assertEqual(client.get(f"/manage/{setup['org'].slug}/e/{setup['event'].pk}/").status_code, 403)

    def test_event_manager_cannot_refund(self):
        setup = make_event()
        order = buy(setup, {"standard": 1})
        manager = make_user("manager@example.com", Role.EVENT_MANAGER, setup["org"])
        client = Client()
        client.force_login(manager)
        url = f"/manage/{setup['org'].slug}/e/{setup['event'].pk}/orders/{order.pk}/"
        client.post(url, {"action": "confirm", "tickets": [order.tickets.get().pk], "amount_choice": "full"})
        self.assertEqual(order.tickets.get().status, Ticket.Status.VALID)

    def test_owner_of_one_org_cannot_see_another(self):
        setup = make_event("one")
        other = make_event("two")
        client = Client()
        client.force_login(setup["owner"])
        self.assertEqual(client.get(f"/manage/{other['org'].slug}/e/{other['event'].pk}/").status_code, 404)
        self.assertEqual(client.get(f"/manage/{setup['org'].slug}/e/{other['event'].pk}/").status_code, 404)


@override_settings(EMAIL_BACKEND=LOCMEM, OCP_PAYMENT_PROVIDER="test")
class Scenario9Exports(TestCase):
    def test_csv_exports_match_the_dashboard(self):
        setup = make_event()
        orders = [buy(setup, {"standard": 2}), buy(setup, {"free": 1}, email="free@example.com")]
        check_in(setup["event"], setup["owner"], code=orders[0].tickets.first().code)
        check_in(setup["event"], setup["owner"], code=orders[0].tickets.first().code)
        client = Client()
        client.force_login(setup["owner"])
        base = f"/manage/{setup['org'].slug}/e/{setup['event'].pk}/"

        attendees = list(csv.reader(io.StringIO(client.get(base + "attendees/?export=csv").content.decode("utf-8-sig"))))
        self.assertEqual(len(attendees) - 1, 3)
        checked_in_rows = [row for row in attendees[1:] if row[7]]
        attendance = list(csv.reader(io.StringIO(client.get(base + "reports/?export=attendance").content.decode("utf-8-sig"))))
        self.assertEqual(len(attendance) - 1, 2)  # one admitted scan and one duplicate, both recorded

        dashboard = client.get(base)
        self.assertEqual(dashboard.context["checked_in"], len(checked_in_rows))
        self.assertEqual(dashboard.context["issued"], len(attendees) - 1)
        orders_csv = list(csv.reader(io.StringIO(client.get(base + "orders/?export=csv").content.decode("utf-8-sig"))))
        self.assertEqual(len(orders_csv) - 1, 2)


@override_settings(EMAIL_BACKEND="tests.helpers.BouncingBackend", OCP_PAYMENT_PROVIDER="test")
class Scenario10FailedEmail(TestCase):
    def test_failed_email_is_visible_and_retry_does_not_issue_new_tickets(self):
        setup = make_event()
        with self.captureOnCommitCallbacks(execute=True):
            order = buy(setup, {"standard": 1}, email="typo@bounce.invalid")
        delivery = Delivery.objects.get(order=order, kind=Delivery.Kind.CONFIRMATION)
        self.assertEqual(delivery.status, Delivery.Status.FAILED)
        self.assertIn("mailbox unavailable", delivery.error)
        ticket_codes = list(order.tickets.values_list("code", flat=True))

        client = Client()
        client.force_login(setup["owner"])
        base = f"/manage/{setup['org'].slug}/e/{setup['event'].pk}/"
        self.assertContains(client.get(base + "emails/"), "typo@bounce.invalid")
        self.assertContains(client.get(base), "Fix the address and send again")

        client.post(base + f"deliveries/{delivery.pk}/retry/", {"email": "fixed@example.com"})
        delivery.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(delivery.status, Delivery.Status.SENT)
        self.assertEqual(delivery.attempts, 2)
        self.assertEqual(order.purchaser_email, "fixed@example.com")
        self.assertEqual(list(order.tickets.values_list("code", flat=True)), ticket_codes)
        self.assertEqual(mail.outbox[-1].to, ["fixed@example.com"])


class SignupAndOrganizations(TestCase):
    def test_signup_creates_owner_and_organization(self):
        client = Client()
        response = client.post("/accounts/signup/", {
            "first_name": "Ada", "last_name": "Lovelace", "email": "Ada@Example.com",
            "password": "correct-horse-battery", "organization": "Analytical Events",
        })
        org = Organization.objects.get(name="Analytical Events")
        self.assertRedirects(response, f"/manage/{org.slug}/", fetch_redirect_response=False)
        self.assertEqual(org.memberships.get().role, Role.OWNER)
        self.assertEqual(org.memberships.get().user.username, "ada@example.com")
