from django.views.decorators.http import require_GET
from ocp.core.api import event_access, paginated
from .models import Attendee


@require_GET
@event_access("view_attendees")
def orders(request, event, member):
    rows = event.orders.all()
    if request.GET.get("status"):
        rows = rows.filter(status=request.GET["status"])
    return paginated(request, rows.values("id", "number", "purchaser_first_name", "purchaser_last_name", "purchaser_email", "status", "total", "refunded_total", "currency", "created_at"))


@require_GET
@event_access("view_attendees")
def attendees(request, event, member):
    rows = Attendee.objects.filter(order__event=event).order_by("last_name", "first_name", "pk")
    query = request.GET.get("q", "").strip()[:100]
    if query:
        from django.db.models import Q
        rows = rows.filter(Q(first_name__icontains=query)|Q(last_name__icontains=query)|Q(email__icontains=query))
    return paginated(request, rows.values("id", "first_name", "last_name", "email", "ticket_type__name", "order__number", "ticket__status", "ticket__checked_in_at"))
