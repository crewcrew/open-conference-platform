"""Dashboard, reports and history (RPT-01 to RPT-04, ORG-06, CHK-08)."""

from collections import OrderedDict
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from ocp.checkin.models import CheckInEvent
from ocp.comms.models import Delivery
from ocp.events.formatting import short_date
from ocp.ticketing.models import ZERO, Order, Refund, RefundRequest, Ticket
from .services import money_summary

from ocp.organizer.context import page
from ocp.organizer.decorators import organizer_view
from ocp.ticketing.views import _csv_response, _local, filtered_orders




def weekly_registrations(event, weeks=20):
    tickets = Ticket.objects.filter(event=event).values_list("created_at", flat=True)
    if not tickets:
        return []
    local_dates = [event.local(t).date() for t in tickets]
    end = max(local_dates)
    start = max(min(local_dates), end - timedelta(weeks=weeks - 1))
    start -= timedelta(days=start.weekday())
    buckets = OrderedDict()
    cursor = start
    while cursor <= end:
        buckets[cursor] = 0
        cursor += timedelta(days=7)
    for day in local_dates:
        if day >= start:
            buckets[day - timedelta(days=day.weekday())] += 1
    peak = max(buckets.values()) or 1
    bars = []
    previous_month = None
    for week, count in buckets.items():
        label = week.strftime("%b") if week.month != previous_month else ""
        previous_month = week.month
        bars.append({"week": short_date(week), "count": count, "height": round(count / peak * 100), "label": label})
    return bars


@organizer_view("view_reports")
def dashboard(request):
    event = request.event
    ticket_types = list(event.ticket_types.all())
    valid = Ticket.objects.filter(event=event, status=Ticket.Status.VALID)
    issued = valid.count()
    checked_in = valid.filter(checked_in_at__isnull=False).count()
    capacity = sum(t.quantity for t in ticket_types if t.is_active)
    sold_by_type = dict(valid.values_list("ticket_type").annotate(n=Count("id")))
    orders = Order.objects.filter(event=event)
    door = (
        CheckInEvent.objects.filter(event=event, result=CheckInEvent.Result.ADMITTED)
        .values("lane").annotate(n=Count("id")).order_by("-n")
    )
    attention = []
    failed_emails = Delivery.objects.filter(event=event, status=Delivery.Status.FAILED).count()
    if failed_emails:
        attention.append(("warn", f"{failed_emails} email{'s' if failed_emails != 1 else ''} didn't send",
                          "Fix the address and send again. Resending never issues new tickets.", "emails", "Review emails"))
    open_requests = RefundRequest.objects.filter(order__event=event, status=RefundRequest.Status.OPEN).count()
    if open_requests:
        attention.append(("info", f"{open_requests} refund request{'s' if open_requests != 1 else ''} waiting",
                          "Attendees asked to cancel from their booking link.", "orders", "Review requests"))
    failed_refunds = Refund.objects.filter(order__event=event, status=Refund.Status.FAILED).count()
    if failed_refunds:
        attention.append(("danger", f"{failed_refunds} refund{'s' if failed_refunds != 1 else ''} failed at the payment provider",
                          "The tickets are cancelled but the money hasn't gone back yet.", "orders", "Review refunds"))
    if not event.is_published and not event.is_cancelled:
        attention.append(("info", "This event is a draft", "Only your team can see it. Publish it when tickets and sessions are ready.", "event_edit", "Review setup"))

    return page(
        request,
        "organizer/dashboard.html",
        {
            "issued": issued,
            "capacity": capacity,
            "remaining": sum(t.available for t in ticket_types if t.is_active),
            "checked_in": checked_in,
            "money": money_summary(orders, event),
            "bars": weekly_registrations(event),
            "by_type": [(t, sold_by_type.get(t.pk, 0)) for t in ticket_types],
            "door": door,
            "door_search": CheckInEvent.objects.filter(event=event, result=CheckInEvent.Result.ADMITTED, method=CheckInEvent.Method.SEARCH).count(),
            "door_invalid": CheckInEvent.objects.filter(event=event, result=CheckInEvent.Result.INVALID).count(),
            "latest_orders": orders.exclude(status=Order.Status.PENDING, details_complete=False).order_by("-created_at")[:6],
            "attention": attention,
            "now": event.local(timezone.now()),
        },
    )


@organizer_view("view_reports")
def reports(request):
    event = request.event
    orders = filtered_orders(event, request.GET)
    if request.GET.get("export") == "attendance":
        response, writer = _csv_response(f"{event.slug}-attendance.csv")
        writer.writerow([f"Time ({event.tz_label})", "Result", "Reason", "Ticket ID", "Attendee", "Ticket type", "Method", "Lane", "Device", "Scanned by", "Synced after offline"])
        for record in CheckInEvent.objects.filter(event=event).select_related("ticket__attendee", "ticket__ticket_type", "actor").order_by("scanned_at"):
            ticket = record.ticket
            writer.writerow([
                _local(event, record.scanned_at), record.get_result_display(), record.reason,
                ticket.display_id if ticket else "", ticket.attendee.full_name if ticket else "",
                ticket.ticket_type.name if ticket else "", record.get_method_display(), record.lane, record.device_id,
                record.actor.get_username() if record.actor else "", "yes" if record.was_offline else "",
            ])
        return response
    by_type = []
    for ticket_type in event.ticket_types.all():
        tickets = Ticket.objects.filter(ticket_type=ticket_type, order__in=orders)
        by_type.append({
            "type": ticket_type,
            "valid": tickets.filter(status=Ticket.Status.VALID).count(),
            "cancelled": tickets.filter(status=Ticket.Status.CANCELLED).count(),
            "checked_in": tickets.filter(checked_in_at__isnull=False).count(),
            "revenue": sum((t.attendee.paid_price for t in tickets.select_related("attendee")), ZERO),
        })
    by_session = [
        {"session": s, "count": s.attendees.filter(ticket__status=Ticket.Status.VALID, order__in=orders).count()}
        for s in event.sessions.exclude(choice_group="")
    ]
    return page(
        request,
        "organizer/reports.html",
        {
            "money": money_summary(orders, event),
            "by_type": by_type,
            "by_session": by_session,
            "params": request.GET,
            "statuses": Order.Status.choices,
            "ticket_types": event.ticket_types.all(),
            "query_string": request.GET.urlencode(),
        },
    )


@organizer_view("view_reports")
def history(request):
    logs = request.event.audit_logs.select_related("actor")[:300]
    return page(request, "organizer/history.html", {"logs": logs})
