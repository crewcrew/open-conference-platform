"""Capacity counters (TKT-03).

Each function is a single conditional UPDATE, so two buyers racing for the
last place cannot both succeed: the database only applies the update while
the condition still holds, and the caller learns from the row count.
"""

from django.db.models import F, Q

from ocp.events.models import Session, TicketType

from .models import Coupon


def reserve_tickets(ticket_type_id, count):
    updated = TicketType.objects.filter(pk=ticket_type_id, reserved__lte=F("quantity") - count).update(
        reserved=F("reserved") + count
    )
    return updated == 1


def release_tickets(ticket_type_id, count):
    TicketType.objects.filter(pk=ticket_type_id, reserved__gte=count).update(reserved=F("reserved") - count)


def reserve_session(session_id):
    updated = Session.objects.filter(
        Q(capacity__isnull=True) | Q(reserved__lt=F("capacity")), pk=session_id
    ).update(reserved=F("reserved") + 1)
    return updated == 1


def release_session(session_id):
    Session.objects.filter(pk=session_id, reserved__gte=1).update(reserved=F("reserved") - 1)


def reserve_coupon(coupon_id):
    updated = Coupon.objects.filter(
        Q(max_redemptions__isnull=True) | Q(used_count__lt=F("max_redemptions")), pk=coupon_id
    ).update(used_count=F("used_count") + 1)
    return updated == 1


def release_coupon(coupon_id):
    Coupon.objects.filter(pk=coupon_id, used_count__gte=1).update(used_count=F("used_count") - 1)
