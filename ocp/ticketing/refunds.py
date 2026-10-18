"""Cancellations and refunds (TKT-08).

A refund cancels the chosen tickets straight away, returns their places, and
asks the payment provider to send the money back. The provider's answer can
come later; until then the refund shows as pending.
"""

from django.db import transaction
from django.utils import timezone

from ocp.accounts import audit
from ocp.events.formatting import long_date, money as fmt_money
from ocp.observability import log_event

from . import inventory
from .models import ZERO, Order, Refund, RefundRequest, Ticket, random_code
from .pricing import money


class RefundError(Exception):
    pass


def policy_percent(event, on_date):
    if event.full_refund_until and on_date <= event.full_refund_until:
        return 100
    if event.partial_refund_until and on_date <= event.partial_refund_until:
        return event.partial_refund_percent
    return 0


def suggest_refund(order, tickets, as_of=None):
    """What the event's refund policy gives for these tickets."""
    event = order.event
    as_of = as_of or timezone.now()
    on_date = event.local(as_of).date()
    base = sum((ticket.attendee.paid_price for ticket in tickets), ZERO)
    percent = policy_percent(event, on_date)
    amount = min(money(base * percent / 100), order.refundable_balance)
    if percent == 100:
        explanation = f"Asked on or before {long_date(event.full_refund_until)}, so the policy gives a full refund."
    elif percent:
        explanation = (
            f"Asked between {long_date(event.full_refund_until) or 'the start of sales'} and "
            f"{long_date(event.partial_refund_until)}, so the policy gives {percent}% back."
        )
    elif event.full_refund_until or event.partial_refund_until:
        explanation = "Asked after the last refund date, so the policy gives no refund."
    else:
        explanation = "This event has no refund dates set."
    return {"percent": percent, "amount": amount, "base": base, "explanation": explanation}


def cancel_and_refund(order, tickets, amount, actor, note="", notify=True, request=None):
    """Cancel `tickets` and refund `amount` (which may be zero)."""
    amount = money(amount)
    tickets = list(tickets)
    if not tickets:
        raise RefundError("Choose at least one ticket to cancel.")
    if any(ticket.order_id != order.pk for ticket in tickets):
        raise RefundError("Those tickets aren't part of this order.")
    if any(not ticket.is_valid for ticket in tickets):
        raise RefundError("One of those tickets is already cancelled.")
    if amount < 0:
        raise RefundError("The refund can't be negative.")
    if amount > order.refundable_balance:
        raise RefundError(f"You can refund at most {fmt_money(order.refundable_balance, order.currency)}.")
    if amount > 0 and order.payment_provider in ("", "free"):
        raise RefundError("This order wasn't paid through a payment provider, so there's nothing to refund.")

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        now = timezone.now()
        for ticket in tickets:
            updated = Ticket.objects.filter(pk=ticket.pk, status=Ticket.Status.VALID).update(
                status=Ticket.Status.CANCELLED, cancelled_at=now
            )
            if not updated:
                raise RefundError("One of those tickets was cancelled a moment ago.")
            inventory.release_tickets(ticket.ticket_type_id, 1)
            for session_id in ticket.attendee.sessions.values_list("id", flat=True):
                inventory.release_session(session_id)

        refund = Refund.objects.create(
            order=order,
            number=f"RF-{order.number}-{random_code(3)}",
            amount=amount,
            status=Refund.Status.PENDING if amount > 0 else Refund.Status.SUCCEEDED,
            note=note,
            request=request,
            provider=order.payment_provider,
            created_by=actor,
            completed_at=None if amount > 0 else now,
        )
        refund.tickets.set(tickets)
        order.refunded_total = money(order.refunded_total + amount)
        order.status = settle_status(order)
        order.save(update_fields=["refunded_total", "status", "updated_at"])

        if request is not None:
            request.status = RefundRequest.Status.APPROVED
            request.resolved_at = now
            request.resolved_by = actor
            request.save(update_fields=["status", "resolved_at", "resolved_by"])

        names = ", ".join(ticket.attendee.full_name or ticket.display_id for ticket in tickets)
        audit.record(
            order.event.organization,
            actor,
            "order.refund" if amount > 0 else "order.cancel",
            f"Cancelled {len(tickets)} ticket(s) on {order.number} ({names}) and refunded {fmt_money(amount, order.currency)}."
            + (f" Note: {note}" if note else ""),
            event=order.event,
            obj=order,
            changes={"amount": str(amount), "tickets": [t.display_id for t in tickets]},
        )

    if amount > 0:
        send_refund_to_provider(refund)
    log_event("order.refunded", order=order.number, amount=amount, tickets=len(tickets))
    if notify:
        from ocp.comms.services import send_cancellation

        send_cancellation(order, tickets, refund)
    return refund


def send_refund_to_provider(refund):
    from .payments import get_provider

    order = refund.order
    try:
        result = get_provider(order.payment_provider).refund(order, refund.amount, refund.number)
    except Exception as error:  # the refund record keeps the failure for retry
        result = None
        refund.error = str(error)
    if result is not None:
        refund.provider_ref = result.ref
        refund.error = result.error
        if result.status == "succeeded":
            refund.status = Refund.Status.SUCCEEDED
            refund.completed_at = timezone.now()
        elif result.status == "failed":
            refund.status = Refund.Status.FAILED
        else:
            refund.status = Refund.Status.PENDING
    else:
        refund.status = Refund.Status.FAILED
    refund.save(update_fields=["provider_ref", "error", "status", "completed_at"])
    if refund.status == Refund.Status.FAILED:
        log_event("refund.failed", refund=refund.number, error=refund.error)
    return refund


def settle_status(order):
    valid_left = order.tickets.filter(status=Ticket.Status.VALID).exists()
    if order.refunded_total <= 0:
        return Order.Status.PAID if valid_left else Order.Status.CANCELLED
    if order.refunded_total >= order.total:
        return Order.Status.REFUNDED
    return Order.Status.PARTIALLY_REFUNDED


def decline_request(request, actor, note=""):
    request.status = RefundRequest.Status.DECLINED
    request.resolved_at = timezone.now()
    request.resolved_by = actor
    request.save(update_fields=["status", "resolved_at", "resolved_by"])
    order = request.order
    audit.record(
        order.event.organization,
        actor,
        "order.refund_declined",
        f"Declined the refund request on {order.number}." + (f" Note: {note}" if note else ""),
        event=order.event,
        obj=order,
    )


def refund_unfulfillable_payment(order_id):
    """Money arrived after the places sold out: give it all back."""
    order = Order.objects.get(pk=order_id)
    refund = Refund.objects.create(
        order=order,
        number=f"RF-{order.number}-{random_code(3)}",
        amount=order.total,
        note="Automatic: payment arrived after the hold expired and the places had sold.",
        provider=order.payment_provider,
    )
    order.refunded_total = order.total
    order.save(update_fields=["refunded_total", "updated_at"])
    send_refund_to_provider(refund)
    log_event("refund.automatic", order=order.number, amount=order.total)
    return refund
