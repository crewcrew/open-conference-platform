from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET
from ocp.accounts.models import Organization, Role
from ocp.accounts.permissions import capabilities_for, membership_for
from ocp.core.api import paginated
from .models import Event, TicketType


def event_data(event):
    return {"id": event.pk, "name": event.name, "slug": event.slug, "summary": event.summary,
            "starts_at": event.starts_at, "ends_at": event.ends_at, "timezone": event.timezone,
            "venue_name": event.venue_name, "status": event.status, "currency": event.currency,
            "public_url": settings.OCP_BASE_URL + reverse("public:event", args=[event.slug])}


@require_GET
def public_events(request):
    rows = Event.objects.filter(status=Event.Status.PUBLISHED, visibility=Event.Visibility.PUBLIC)
    return JsonResponse({"results": [event_data(e) for e in rows[:100]]})


@require_GET
def public_event(request, slug):
    event = get_object_or_404(Event, slug=slug, status=Event.Status.PUBLISHED)
    data = event_data(event)
    data.update(description=event.description, venue_address=event.venue_address,
                accessibility_info=event.accessibility_info, refund_policy=event.refund_policy,
                booking_fee=event.booking_fee, tax_name=event.tax_name, tax_rate=event.tax_rate,
                prices_include_tax=event.prices_include_tax, contact_email=event.contact_email)
    data["ticket_types"] = [{"id": t.pk, "name": t.name, "description": t.description,
                             "price": t.price, "available": t.available, "sale_state": t.sale_state()}
                            for t in event.ticket_types.filter(visibility=TicketType.Visibility.PUBLIC, is_active=True)]
    data["sessions"] = list(event.sessions.values("id", "title", "kind", "speakers", "room", "starts_at", "ends_at", "description"))
    return JsonResponse(data)


@require_GET
def organization_events(request, org_slug):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "authentication_required"}, status=401)
    org = get_object_or_404(Organization, slug=org_slug)
    member = membership_for(request.user, org)
    if member is None:
        return JsonResponse({"error": "not_found"}, status=404)
    rows = org.events.all()
    if member.role == Role.VOLUNTEER:
        rows = rows.filter(pk__in=member.events.values("pk"))
    return JsonResponse({"results": [{**event_data(e), "capabilities": sorted(capabilities_for(member,e)),
                                     "manage_url": settings.OCP_BASE_URL + reverse("organizer:dashboard", args=[org.slug,e.pk]),
                                     "scanner_url": settings.OCP_BASE_URL + reverse("checkin:scanner", args=[e.pk])} for e in rows[:100]]})
