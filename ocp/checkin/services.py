"""Check-in rules (CHK-02, CHK-03, CHK-07).

The first valid scan admits the attendee. Any later scan of the same ticket
reports who admitted them and when, without a second admission. Cancelled,
refunded and unknown tickets are rejected with a reason.
"""

from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from ocp.events.formatting import long_date, time_24
from ocp.observability import log_event
from ocp.ticketing.models import Order, Ticket

from .models import CheckInEvent


def _parse_time(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if timezone.is_naive(parsed):
        return None
    if parsed > timezone.now() + timedelta(minutes=5):
        return None
    return parsed


def check_in(event, actor, *, code=None, ticket=None, lane="", device_id="", method=CheckInEvent.Method.SCAN,
             client_scan_id=None, scanned_at=None, was_offline=False):
    if client_scan_id:
        existing = CheckInEvent.objects.filter(client_scan_id=client_scan_id).select_related("ticket").first()
        if existing:
            return existing

    when = _parse_time(scanned_at) or timezone.now()
    if ticket is None and code:
        ticket = (
            Ticket.objects.filter(code=code.strip())
            .select_related("attendee", "ticket_type", "order", "checked_in_by")
            .first()
        )

    result, reason = CheckInEvent.Result.INVALID, ""
    if ticket is None:
        reason = "We don't recognise this code."
    elif ticket.event_id != event.pk:
        reason = "This ticket is for a different event."
        ticket = None
    elif not ticket.is_valid:
        reason = _invalid_reason(ticket, event)
    else:
        admitted = Ticket.objects.filter(pk=ticket.pk, status=Ticket.Status.VALID, checked_in_at__isnull=True).update(
            checked_in_at=when, checked_in_by=actor, checked_in_lane=lane[:60]
        )
        result = CheckInEvent.Result.ADMITTED if admitted else CheckInEvent.Result.DUPLICATE
        ticket.refresh_from_db()

    try:
        with transaction.atomic():
            record = CheckInEvent.objects.create(
                event=event,
                ticket=ticket,
                scanned_code=(code or "")[:200],
                result=result,
                reason=reason,
                method=method,
                actor=actor,
                lane=lane[:60],
                device_id=device_id[:80],
                client_scan_id=client_scan_id or None,
                was_offline=was_offline,
                scanned_at=when,
            )
    except IntegrityError:
        return CheckInEvent.objects.get(client_scan_id=client_scan_id)
    log_event("checkin.scan", event=event.slug, result=result, lane=lane or "-", offline=was_offline)
    return record


def _invalid_reason(ticket, event):
    when = event.local(ticket.cancelled_at) if ticket.cancelled_at else None
    refunded = ticket.refunds.filter(amount__gt=0).exists() or ticket.order.status == Order.Status.REFUNDED
    verb = "refunded" if refunded else "cancelled"
    return f"This ticket was {verb} on {long_date(when)}." if when else f"This ticket was {verb}."


def describe(record, event):
    """What the scanner shows: the minimum needed at the door (CHK-05)."""
    ticket = record.ticket
    data = {
        "result": record.result,
        "label": record.get_result_display(),
        "reason": record.reason,
        "scanned_at": time_24(event.local(record.scanned_at)),
    }
    if ticket is not None:
        attendee = ticket.attendee
        data.update(
            {
                "name": attendee.full_name,
                "ticket_type": ticket.ticket_type.name,
                "ticket_id": ticket.display_id,
                "sessions": [s.title for s in attendee.sessions.exclude(choice_group="").order_by("starts_at")],
            }
        )
        if record.result == CheckInEvent.Result.DUPLICATE and ticket.checked_in_at:
            by = ticket.checked_in_by
            data["first_scan"] = {
                "time": time_24(event.local(ticket.checked_in_at)),
                "lane": ticket.checked_in_lane,
                "by": (by.first_name or by.get_username()) if by else "",
            }
    return data


def stats(event):
    valid = Ticket.objects.filter(event=event, status=Ticket.Status.VALID)
    total = valid.count()
    checked_in = valid.filter(checked_in_at__isnull=False).count()
    return {"checked_in": checked_in, "total": total, "to_go": total - checked_in}
