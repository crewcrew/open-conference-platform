from django.http import JsonResponse
from django.views.decorators.http import require_GET
from ocp.core.api import event_access
from ocp.ticketing.models import Ticket
from .services import money_summary


@require_GET
@event_access("view_reports")
def dashboard(request, event, member):
    tickets = Ticket.objects.filter(order__event=event, status=Ticket.Status.VALID)
    return JsonResponse({"event_id": event.pk, "currency": event.currency,
                         "tickets_issued": tickets.count(),
                         "checked_in": tickets.filter(checked_in_at__isnull=False).count(),
                         "money": money_summary(event.orders.all(), event)})
