from django.shortcuts import render

from ocp.comms.models import Delivery
from ocp.ticketing.models import Refund, RefundRequest


NAV = {
    "dashboard": "dashboard",
    "event_edit": "setup",
    "sessions": "setup",
    "tickets": "setup",
    "questions": "setup",
    "attendees": "attendees",
    "attendee_edit": "attendees",
    "orders": "orders",
    "order_detail": "orders",
    "coupons": "coupons",
    "emails": "emails",
    "compose": "emails",
    "email_detail": "emails",
    "reports": "reports",
    "history": "history",
    "org": "events",
    "event_create": "events",
    "team": "team",
    "member_edit": "team",
    "org_settings": "org_settings",
}


def page(request, template, context=None, **kwargs):
    """Render an organizer page with the shell's shared context."""
    event = getattr(request, "event", None)
    url_name = request.resolver_match.url_name if request.resolver_match else ""
    data = {
        "org": getattr(request, "org", None),
        "membership": getattr(request, "membership", None),
        "event": event,
        "caps": getattr(request, "caps", set()),
        "memberships": request.user.memberships.select_related("organization"),
        "nav": NAV.get(url_name, ""),
        "tab": url_name,
    }
    if event is not None:
        data["nav_counts"] = {
            "refunds": RefundRequest.objects.filter(order__event=event, status=RefundRequest.Status.OPEN).count()
            + Refund.objects.filter(order__event=event, status=Refund.Status.FAILED).count(),
            "emails": Delivery.objects.filter(event=event, status=Delivery.Status.FAILED).count(),
        }
    data.update(context or {})
    return render(request, template, data, **kwargs)
