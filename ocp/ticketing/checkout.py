"""Checkout: hold places, apply a coupon, collect details, confirm payment.

An order starts `pending` with its places held until `hold_expires_at`.
Tickets are only issued when payment is confirmed, and confirming twice
issues them once (acceptance scenarios 1, 2 and 3).
"""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from ocp.events.formatting import long_date
from ocp.events.models import TicketType
from ocp.observability import log_event

from . import inventory
from .models import Attendee, Coupon, Order, Redemption, Ticket, random_code
from .pricing import price_order


class CheckoutError(Exception):
    """A problem the buyer can understand and fix."""


# Placing an order ----------------------------------------------------------


def start_order(event, quantities, access_code=""):
    """Hold the requested tickets. `quantities` maps TicketType id to count."""
    if not event.is_published:
        raise CheckoutError("Registration isn't open for this event.")
    release_expired_holds(event)

    now = timezone.now()
    wanted = []
    for ticket_type in event.ticket_types.filter(pk__in=quantities.keys()):
        count = quantities.get(ticket_type.pk, 0)
        if count <= 0:
            continue
        if ticket_type.visibility == TicketType.Visibility.HIDDEN and (
            not access_code or access_code.strip().lower() != ticket_type.access_code.strip().lower()
        ):
            raise CheckoutError(f"{ticket_type.name} needs a valid access code.")
        state = ticket_type.sale_state(now)
        if state != "on_sale":
            messages = {
                "not_started": f"{ticket_type.name} isn't on sale yet.",
                "ended": f"Sales for {ticket_type.name} have ended.",
                "sold_out": f"{ticket_type.name} has sold out.",
                "closed": f"{ticket_type.name} isn't available.",
            }
            raise CheckoutError(messages[state])
        if count < ticket_type.min_per_order:
            raise CheckoutError(f"Choose at least {ticket_type.min_per_order} {ticket_type.name} tickets.")
        if count > ticket_type.max_per_order:
            raise CheckoutError(f"You can buy up to {ticket_type.max_per_order} {ticket_type.name} tickets per order.")
        wanted.append((ticket_type, count))

    if not wanted:
        raise CheckoutError("Choose at least one ticket.")

    with transaction.atomic():
        for ticket_type, count in wanted:
            if not inventory.reserve_tickets(ticket_type.pk, count):
                left = TicketType.objects.get(pk=ticket_type.pk).available
                if left:
                    raise CheckoutError(f"Only {left} {ticket_type.name} tickets are left.")
                raise CheckoutError(f"{ticket_type.name} has just sold out.")
        order = _create_order(event, now)
        position = 0
        for ticket_type, count in wanted:
            for _ in range(count):
                Attendee.objects.create(
                    order=order, ticket_type=ticket_type, position=position, unit_price=ticket_type.price
                )
                position += 1
        price_order(order)

    log_event("checkout.started", order=order.number, event=event.slug, tickets=position)
    return order


def _create_order(event, now):
    for _ in range(8):
        number = f"{event.order_prefix}-{random_code(4)}"
        if Order.objects.filter(number=number).exists():
            continue
        try:
            with transaction.atomic():
                return Order.objects.create(
                    event=event,
                    number=number,
                    currency=event.currency,
                    hold_expires_at=now + timedelta(minutes=event.hold_minutes),
                )
        except IntegrityError:
            continue
    raise CheckoutError("We couldn't start your order. Please try again.")


def hold_is_live(order):
    return order.status == Order.Status.PENDING and order.hold_expires_at and order.hold_expires_at > timezone.now()


# Coupons -------------------------------------------------------------------


def apply_coupon(order, code):
    """Validate and attach a coupon (CPN-03). One coupon per order (CPN-08)."""
    code = (code or "").strip().upper()
    if not code:
        raise CheckoutError("Enter a coupon code.")
    coupon = Coupon.objects.filter(event=order.event, code=code).first()
    if coupon is None:
        raise CheckoutError(f"We don't recognise the code {code}.")
    if order.coupon_id == coupon.pk:
        return coupon
    now = timezone.now()
    state = coupon.state(now)
    local = order.event.local
    if state == "disabled":
        raise CheckoutError(f"{code} can't be used any more.")
    if state == "scheduled":
        raise CheckoutError(f"{code} starts on {long_date(local(coupon.starts_at))}.")
    if state == "expired":
        raise CheckoutError(f"{code} ended on {long_date(local(coupon.ends_at))}, so it can't be used.")
    eligible_ids = set(coupon.ticket_types.values_list("id", flat=True))
    if not order.attendees.filter(ticket_type_id__in=eligible_ids, unit_price__gt=0).exists():
        names = ", ".join(coupon.ticket_types.values_list("name", flat=True))
        raise CheckoutError(f"{code} only applies to {names} tickets.")

    with transaction.atomic():
        if not inventory.reserve_coupon(coupon.pk):
            raise CheckoutError(f"{code} has been used up.")
        if order.coupon_id:
            inventory.release_coupon(order.coupon_id)
        order.coupon = coupon
        order.save(update_fields=["coupon", "updated_at"])
        price_order(order)
    return coupon


def remove_coupon(order):
    if not order.coupon_id:
        return
    with transaction.atomic():
        inventory.release_coupon(order.coupon_id)
        order.coupon = None
        order.save(update_fields=["coupon", "updated_at"])
        price_order(order)


# Details -------------------------------------------------------------------


def save_details(order, purchaser, attendees_data):
    """Store purchaser and attendee details and hold chosen sessions.

    `purchaser` is a dict of purchaser fields. `attendees_data` maps attendee
    id to {first_name, last_name, email, answers, session_ids}.
    """
    with transaction.atomic():
        for field in ("purchaser_first_name", "purchaser_last_name", "purchaser_email", "purchaser_organisation"):
            setattr(order, field, purchaser.get(field, ""))
        order.purchaser_answers = purchaser.get("answers", {})
        order.marketing_consent = bool(purchaser.get("marketing_consent"))

        for attendee in order.attendees.select_related("ticket_type"):
            data = attendees_data[attendee.pk]
            attendee.first_name = data["first_name"]
            attendee.last_name = data["last_name"]
            attendee.email = data["email"]
            attendee.answers = data.get("answers", {})
            attendee.is_purchaser = bool(data.get("is_purchaser"))
            attendee.save()

            old = set(attendee.sessions.values_list("id", flat=True))
            new = set(data.get("session_ids", []))
            for session_id in new - old:
                if not inventory.reserve_session(session_id):
                    session = order.event.sessions.get(pk=session_id)
                    raise CheckoutError(f"{session.title} has just filled up. Please choose another session.")
            for session_id in old - new:
                inventory.release_session(session_id)
            attendee.sessions.set(new)

        order.details_complete = True
        order.save()


# Payment -------------------------------------------------------------------


def begin_payment(order, success_url, cancel_url):
    """Return the URL to send the buyer to next."""
    from .payments import get_provider

    if not hold_is_live(order):
        raise CheckoutError("Your hold on these tickets has expired. Please start again.")
    if not order.details_complete:
        raise CheckoutError("Fill in the details for every ticket first.")
    if order.total == 0:
        confirm_paid(order.pk, provider="free", payment_ref="")
        return success_url
    provider = get_provider()
    session = provider.create_checkout(order, success_url=success_url, cancel_url=cancel_url)
    order.payment_provider = provider.name
    order.payment_ref = session.ref
    order.save(update_fields=["payment_provider", "payment_ref", "updated_at"])
    log_event("payment.started", order=order.number, provider=provider.name, amount=order.total)
    return session.url


def confirm_paid(order_id, provider, payment_ref, amount=None, payment_intent=""):
    """Mark an order paid and issue its tickets. Safe to call more than once."""
    from .refunds import refund_unfulfillable_payment

    issued = False
    with transaction.atomic():
        order = Order.objects.select_for_update().select_related("event").get(pk=order_id)
        if order.is_confirmed:
            return order
        if amount is not None and amount != order.total:
            log_event("payment.amount_mismatch", order=order.number, expected=order.total, received=amount)
            was_pending = order.status == Order.Status.PENDING
            order.status = Order.Status.FAILED
            order.failure_reason = f"Payment amount {amount} did not match order total {order.total}."
            order.save()
            if was_pending:
                _release_holds(order)
            return order
        if order.status in (Order.Status.EXPIRED, Order.Status.FAILED):
            if not _rehold(order):
                order.status = Order.Status.FAILED
                order.failure_reason = "Paid after the hold expired and the places had gone."
                order.payment_ref = payment_ref or order.payment_ref
                order.payment_intent = payment_intent or order.payment_intent
                order.save()
                transaction.on_commit(lambda: refund_unfulfillable_payment(order.pk))
                return order
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.payment_provider = provider
        order.payment_ref = payment_ref or order.payment_ref
        order.payment_intent = payment_intent or order.payment_intent
        order.failure_reason = ""
        order.save()
        for attendee in order.attendees.select_related("ticket_type"):
            Ticket.objects.get_or_create(
                attendee=attendee,
                defaults={"order": order, "event": order.event, "ticket_type": attendee.ticket_type},
            )
        if order.coupon_id:
            Redemption.objects.get_or_create(
                order=order, defaults={"coupon_id": order.coupon_id, "discount_amount": order.discount_total}
            )
        issued = True

    if issued:
        log_event("payment.confirmed", order=order.number, provider=provider, amount=order.total)
        from ocp.comms.services import send_order_confirmation

        transaction.on_commit(lambda: send_order_confirmation(order))
    return order


def mark_failed(order, reason):
    """Payment was declined or abandoned: release the places now."""
    updated = Order.objects.filter(pk=order.pk, status=Order.Status.PENDING).update(
        status=Order.Status.FAILED, failure_reason=reason[:300], updated_at=timezone.now()
    )
    if updated:
        _release_holds(order)
        log_event("payment.failed", order=order.number, reason=reason)


def cancel_checkout(order):
    updated = Order.objects.filter(pk=order.pk, status=Order.Status.PENDING).update(
        status=Order.Status.EXPIRED, updated_at=timezone.now()
    )
    if updated:
        _release_holds(order)


def release_expired_holds(event=None):
    """Free places held by checkouts that ran out of time."""
    expired = Order.objects.filter(status=Order.Status.PENDING, hold_expires_at__lt=timezone.now())
    if event is not None:
        expired = expired.filter(event=event)
    count = 0
    for order in expired:
        updated = Order.objects.filter(pk=order.pk, status=Order.Status.PENDING).update(
            status=Order.Status.EXPIRED, updated_at=timezone.now()
        )
        if updated:
            _release_holds(order)
            count += 1
    return count


def _release_holds(order):
    counts = {}
    for attendee in order.attendees.all():
        counts[attendee.ticket_type_id] = counts.get(attendee.ticket_type_id, 0) + 1
        for session_id in attendee.sessions.values_list("id", flat=True):
            inventory.release_session(session_id)
    for ticket_type_id, count in counts.items():
        inventory.release_tickets(ticket_type_id, count)
    if order.coupon_id:
        inventory.release_coupon(order.coupon_id)


def _rehold(order):
    """Take the places back for a payment that arrived after the hold expired."""
    counts = {}
    for attendee in order.attendees.all():
        counts[attendee.ticket_type_id] = counts.get(attendee.ticket_type_id, 0) + 1
    try:
        with transaction.atomic():
            for ticket_type_id, count in counts.items():
                if not inventory.reserve_tickets(ticket_type_id, count):
                    raise CheckoutError("sold out")
            for attendee in order.attendees.all():
                for session_id in attendee.sessions.values_list("id", flat=True):
                    if not inventory.reserve_session(session_id):
                        raise CheckoutError("session full")
            if order.coupon_id and not inventory.reserve_coupon(order.coupon_id):
                raise CheckoutError("coupon used up")
    except CheckoutError:
        return False
    return True

