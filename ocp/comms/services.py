"""Sending email (COM-01 to COM-06).

Every email is stored as a Delivery before it is sent, so a failure is
visible to organizers and can be retried. Retrying sends the same tickets
again; it never issues new ones (acceptance scenario 10).
"""

import re
from email.utils import formataddr, parseaddr

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.template.backends.django import DjangoTemplates
from django.urls import reverse
from django.utils import timezone

from ocp.events.formatting import date_range
from ocp.observability import log_event
from ocp.ticketing.models import Attendee, Order, Ticket

from .models import Communication, Delivery, Unsubscribe


def absolute(path):
    return f"{settings.OCP_BASE_URL}{path}"


def booking_url(order):
    return absolute(reverse("public:booking", args=[order.access_token]))


def ticket_url(ticket):
    return absolute(reverse("public:ticket", args=[ticket.code]))


def event_context(event):
    return {
        "event": event,
        "event_dates": date_range(event.local(event.starts_at), event.local(event.ends_at)),
        "event_url": absolute(reverse("public:event", args=[event.slug])),
        "calendar_url": absolute(reverse("public:calendar", args=[event.slug])),
    }


def _from_address(event):
    _, address = parseaddr(settings.DEFAULT_FROM_EMAIL)
    if event is None or not address:
        return settings.DEFAULT_FROM_EMAIL
    return formataddr((event.name, address))


_engine = None


def _email_engine():
    """Plain-text email templates, rendered without HTML escaping."""
    global _engine
    if _engine is None:
        _engine = DjangoTemplates(
            {
                "NAME": "email",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {"autoescape": False},
            }
        )
    return _engine


def render_email(template, context):
    """Templates start with a `Subject:` line, then a blank line, then the body."""
    text = _email_engine().get_template(f"emails/{template}.txt").render(context).strip()
    first, _, body = text.partition("\n")
    subject = first.removeprefix("Subject:").strip()
    body = re.sub(r"\n{3,}", "\n\n", body.strip()) + "\n"
    return subject, body


def send_delivery(delivery):
    delivery.attempts += 1
    delivery.last_attempt_at = timezone.now()
    event = delivery.event
    message = EmailMessage(
        subject=delivery.subject,
        body=delivery.body,
        from_email=_from_address(event),
        to=[delivery.to_email],
        reply_to=[event.contact_email] if event else None,
    )
    try:
        message.send(fail_silently=False)
    except Exception as error:  # every failure is kept on the delivery
        delivery.status = Delivery.Status.FAILED
        delivery.error = str(error)[:1000] or error.__class__.__name__
        log_event("email.failed", delivery=delivery.pk, kind=delivery.kind, error=delivery.error)
    else:
        delivery.status = Delivery.Status.SENT
        delivery.error = ""
        delivery.sent_at = timezone.now()
    delivery.save()
    return delivery


def deliver(kind, to_email, subject, body, *, event=None, order=None, attendee=None, communication=None):
    delivery = Delivery.objects.create(
        kind=kind,
        to_email=to_email,
        subject=subject,
        body=body,
        event=event,
        order=order,
        attendee=attendee,
        communication=communication,
    )
    return send_delivery(delivery)


def retry_delivery(delivery, new_email=None):
    if new_email:
        delivery.to_email = new_email
    return send_delivery(delivery)


# Transactional email -----------------------------------------------------------


def send_order_confirmation(order):
    """Receipt and all tickets to the purchaser; each other attendee gets their own ticket."""
    order = Order.objects.select_related("event").get(pk=order.pk)
    event = order.event
    tickets = list(
        Ticket.objects.filter(order=order).select_related("attendee", "ticket_type").order_by("attendee__position")
    )
    context = {
        **event_context(event),
        "order": order,
        "tickets": [(ticket, ticket_url(ticket)) for ticket in tickets],
        "booking_url": booking_url(order),
    }
    subject, body = render_email("confirmation", context)
    deliver(Delivery.Kind.CONFIRMATION, order.purchaser_email, subject, body, event=event, order=order)

    purchaser = order.purchaser_email.lower()
    for ticket in tickets:
        attendee = ticket.attendee
        if attendee.email and attendee.email.lower() != purchaser:
            send_attendee_ticket(attendee)


def send_attendee_ticket(attendee):
    ticket = attendee.ticket
    order = attendee.order
    event = order.event
    context = {
        **event_context(event),
        "order": order,
        "attendee": attendee,
        "ticket": ticket,
        "sessions": list(attendee.sessions.order_by("starts_at")),
        "ticket_url": ticket_url(ticket),
    }
    subject, body = render_email("ticket", context)
    return deliver(Delivery.Kind.TICKET, attendee.email, subject, body, event=event, order=order, attendee=attendee)


def send_cancellation(order, tickets, refund):
    event = order.event
    context = {**event_context(event), "order": order, "tickets": tickets, "refund": refund, "booking_url": booking_url(order)}
    subject, body = render_email("cancellation", context)
    sent = set()
    if order.purchaser_email:
        deliver(Delivery.Kind.CANCELLATION, order.purchaser_email, subject, body, event=event, order=order)
        sent.add(order.purchaser_email.lower())
    for ticket in tickets:
        email = ticket.attendee.email
        if email and email.lower() not in sent:
            deliver(Delivery.Kind.CANCELLATION, email, subject, body, event=event, order=order, attendee=ticket.attendee)
            sent.add(email.lower())


def send_booking_links(email):
    """Send links to every confirmed booking made with this email. Says nothing
    either way, so the form can't be used to find out who has booked."""
    orders = list(
        Order.objects.filter(purchaser_email__iexact=email.strip(), status__in=Order.CONFIRMED_STATUSES)
        .select_related("event")
        .order_by("-created_at")
    )
    if not orders:
        return None
    context = {"orders": [(order, booking_url(order)) for order in orders]}
    subject, body = render_email("booking_links", context)
    return deliver(Delivery.Kind.BOOKING_LINK, email.strip(), subject, body, event=orders[0].event)


# Organizer messages ---------------------------------------------------------------

MERGE_FIELDS = ["{first name}", "{ticket type}", "{workshop}", "{booking link}"]


def audience_attendees(event, audience):
    attendees = Attendee.objects.filter(order__event=event, ticket__status=Ticket.Status.VALID)
    if audience.get("ticket_type"):
        attendees = attendees.filter(ticket_type_id=audience["ticket_type"])
    if audience.get("session"):
        attendees = attendees.filter(sessions__id=audience["session"])
    if audience.get("attendance") == "checked_in":
        attendees = attendees.filter(ticket__checked_in_at__isnull=False)
    elif audience.get("attendance") == "not_checked_in":
        attendees = attendees.filter(ticket__checked_in_at__isnull=True)
    return attendees.select_related("order", "ticket_type").distinct().order_by("order_id", "position")


def recipients(communication):
    """[(email, attendee, order)], one per email address."""
    event = communication.event
    attendees = audience_attendees(event, communication.audience)
    seen, result = set(), []
    if communication.kind == Communication.Kind.MARKETING:
        blocked = set(
            Unsubscribe.objects.filter(organization=event.organization).values_list("email", flat=True)
        )
        orders = Order.objects.filter(pk__in=attendees.values("order_id"), marketing_consent=True)
        for order in orders:
            email = order.purchaser_email.lower()
            if email and email not in seen and email not in blocked:
                seen.add(email)
                attendee = order.attendees.filter(is_purchaser=True).first()
                result.append((order.purchaser_email, attendee, order))
        return result
    for attendee in attendees:
        email = (attendee.email or attendee.order.purchaser_email).lower()
        if email and email not in seen:
            seen.add(email)
            result.append((attendee.email or attendee.order.purchaser_email, attendee, attendee.order))
    return result


def merge(text, attendee, order):
    sessions = ", ".join(attendee.sessions.exclude(choice_group="").values_list("title", flat=True)) if attendee else ""
    first_name = (attendee.first_name if attendee else "") or order.purchaser_first_name or "there"
    values = {
        "{first name}": first_name,
        "{ticket type}": attendee.ticket_type.name if attendee else "",
        "{workshop}": sessions,
        "{booking link}": booking_url(order),
    }
    for key, value in values.items():
        text = text.replace(key, value)
    return text


def unsubscribe_token(organization, email):
    return signing.dumps({"o": organization.pk, "e": email.lower()}, salt="ocp.unsubscribe")


def read_unsubscribe_token(token):
    return signing.loads(token, salt="ocp.unsubscribe")


def build_message(communication, email, attendee, order):
    event = communication.event
    unsubscribe_url = ""
    if communication.kind == Communication.Kind.MARKETING:
        unsubscribe_url = absolute(reverse("public:unsubscribe", args=[unsubscribe_token(event.organization, email)]))
    context = {
        **event_context(event),
        "communication": communication,
        "message": merge(communication.body, attendee, order),
        "attendee": attendee,
        "ticket": getattr(attendee, "ticket", None) if attendee else None,
        "booking_url": booking_url(order),
        "unsubscribe_url": unsubscribe_url,
    }
    _, body = render_email("update", context)
    return merge(communication.subject, attendee, order), body


def send_communication(communication):
    """Send now. Safe if two workers pick up the same scheduled message."""
    claimed = Communication.objects.filter(
        pk=communication.pk, status__in=[Communication.Status.DRAFT, Communication.Status.SCHEDULED]
    ).update(status=Communication.Status.SENT, sent_at=timezone.now())
    if not claimed:
        return 0
    communication.refresh_from_db()
    people = recipients(communication)
    kind = Delivery.Kind.MARKETING if communication.kind == Communication.Kind.MARKETING else Delivery.Kind.UPDATE
    for email, attendee, order in people:
        subject, body = build_message(communication, email, attendee, order)
        deliver(kind, email, subject, body, event=communication.event, order=order, attendee=attendee, communication=communication)
    Communication.objects.filter(pk=communication.pk).update(recipient_count=len(people))
    log_event("comms.sent", communication=communication.pk, recipients=len(people))
    return len(people)


def process_due(now=None):
    """Send scheduled messages that are due. Run every minute from cron."""
    from ocp.ticketing.checkout import release_expired_holds

    now = now or timezone.now()
    release_expired_holds()
    due = Communication.objects.filter(status=Communication.Status.SCHEDULED, scheduled_for__lte=now)
    sent = 0
    for communication in due:
        sent += send_communication(communication)
    return sent


def failed_deliveries(event):
    return Delivery.objects.filter(event=event, status=Delivery.Status.FAILED).select_related("attendee", "order")


def latest_delivery_by_attendee(event):
    """{attendee id: Delivery} for the newest ticket or confirmation email per attendee."""
    result = {}
    deliveries = Delivery.objects.filter(
        event=event, kind__in=[Delivery.Kind.CONFIRMATION, Delivery.Kind.TICKET]
    ).order_by("created_at")
    for delivery in deliveries:
        if delivery.attendee_id:
            result[delivery.attendee_id] = delivery
        elif delivery.order_id:
            for attendee_id in Attendee.objects.filter(
                Q(email__iexact=delivery.to_email) | Q(email=""), order_id=delivery.order_id
            ).values_list("id", flat=True):
                result[attendee_id] = delivery
    return result


def on_commit_send(func, *args):
    transaction.on_commit(lambda: func(*args))
