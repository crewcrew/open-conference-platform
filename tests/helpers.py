from datetime import timedelta
from decimal import Decimal
from smtplib import SMTPRecipientsRefused

from django.contrib.auth import get_user_model
from django.core.mail.backends.locmem import EmailBackend as LocmemBackend
from django.utils import timezone

from ocp.accounts.models import Membership, Organization, Role
from ocp.events.models import Event, Session, TicketType
from ocp.ticketing import checkout
from ocp.ticketing.models import Coupon
from ocp.ticketing.payments import ProviderEvent, process_provider_event

User = get_user_model()


class BouncingBackend(LocmemBackend):
    """Like the in-memory test backend, but rejects any address at bounce.invalid."""

    def send_messages(self, messages):
        for message in messages:
            for address in message.to:
                if address.endswith("@bounce.invalid"):
                    raise SMTPRecipientsRefused({address: (550, b"5.1.1 mailbox unavailable")})
        return super().send_messages(messages)


def make_user(email, role=None, organization=None):
    user = User.objects.create_user(username=email, email=email, password="a-long-test-password", first_name=email.split("@")[0].title())
    if organization and role:
        Membership.objects.create(user=user, organization=organization, role=role)
    return user


def make_event(slug="testconf", quantity=10, workshop_capacity=2):
    org = Organization.objects.create(name=f"Org {slug}", slug=f"org-{slug}", contact_email="team@example.com")
    owner = make_user(f"owner@{slug}.example", Role.OWNER, org)
    start = timezone.now() + timedelta(days=60)
    event = Event.objects.create(
        organization=org, name=f"Conf {slug}", slug=slug, timezone="Pacific/Auckland",
        starts_at=start, ends_at=start + timedelta(days=1, hours=8), venue_name="Hall", contact_email="help@example.com",
        status=Event.Status.PUBLISHED, booking_fee=Decimal("6.00"), order_prefix="TC",
        full_refund_until=(start - timedelta(days=30)).date(), partial_refund_until=(start - timedelta(days=7)).date(),
        partial_refund_percent=50,
    )
    workshop_a = Session.objects.create(event=event, title="Workshop A", kind="workshop", starts_at=start, ends_at=start + timedelta(hours=3),
                                        capacity=workshop_capacity, choice_group="Workshop")
    workshop_b = Session.objects.create(event=event, title="Workshop B", kind="workshop", starts_at=start, ends_at=start + timedelta(hours=3),
                                        capacity=workshop_capacity, choice_group="Workshop")
    standard = TicketType.objects.create(event=event, name="Standard", price=Decimal("495.00"), quantity=quantity)
    standard.sessions.set([workshop_a, workshop_b])
    free = TicketType.objects.create(event=event, name="Community", price=Decimal("0.00"), quantity=quantity)
    student = TicketType.objects.create(event=event, name="Student", price=Decimal("145.00"), quantity=quantity)
    coupon = Coupon.objects.create(event=event, code="SAVE20", kind=Coupon.Kind.PERCENT, amount=Decimal("20"), max_redemptions=5)
    coupon.ticket_types.set([standard])
    return {
        "org": org, "owner": owner, "event": event, "standard": standard, "free": free, "student": student,
        "coupon": coupon, "workshop_a": workshop_a, "workshop_b": workshop_b,
    }


def fill_details(order, email="buyer@example.com", sessions=None, consent=False):
    attendees = {}
    for index, attendee in enumerate(order.attendees.order_by("position")):
        attendees[attendee.pk] = {
            "first_name": f"Person{index}",
            "last_name": "Test",
            "email": email if index == 0 else f"person{index}@example.com",
            "is_purchaser": index == 0,
            "answers": {},
            "session_ids": [sessions[index]] if sessions else [],
        }
    checkout.save_details(order, {
        "purchaser_first_name": "Person0", "purchaser_last_name": "Test", "purchaser_email": email,
        "purchaser_organisation": "", "marketing_consent": consent, "answers": {},
    }, attendees)
    order.refresh_from_db()
    return order


def buy(setup, quantities, coupon=None, email="buyer@example.com", sessions=None, pay=True, consent=False):
    """Run the whole checkout. Returns the order (paid unless pay=False)."""
    order = checkout.start_order(setup["event"], {setup[name].pk: count for name, count in quantities.items()})
    if coupon:
        checkout.apply_coupon(order, coupon)
    if sessions is None and any(name == "standard" for name in quantities):
        sessions = [setup["workshop_a"].pk if i % 2 == 0 else setup["workshop_b"].pk for i in range(sum(quantities.values()))]
    fill_details(order, email=email, sessions=sessions, consent=consent)
    if not pay:
        return order
    checkout.begin_payment(order, success_url="/done/", cancel_url="/back/")
    order.refresh_from_db()
    if order.total:
        process_provider_event("test", ProviderEvent(event_id=f"{order.payment_ref}:paid", kind="paid", payment_ref=order.payment_ref, amount=order.total))
    order.refresh_from_db()
    return order
