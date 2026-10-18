from django.views.decorators.http import require_GET
from ocp.core.api import event_access, paginated
from .models import Communication


@require_GET
@event_access("send_comms")
def communications(request, event, member):
    return paginated(request, Communication.objects.filter(event=event).order_by("-pk").values(
        "id", "subject", "kind", "status", "scheduled_for", "sent_at", "recipient_count"))
