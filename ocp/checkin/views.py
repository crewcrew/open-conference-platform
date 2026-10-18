"""Mobile check-in (CHK-01 to CHK-07). Volunteers only reach events they're assigned to."""

import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from ocp.accounts.permissions import can, membership_for
from ocp.events.models import Event
from ocp.ticketing.models import Attendee, Ticket

from .models import CheckInEvent
from .services import check_in, describe, stats


def _event_for(request, event_id):
    event = get_object_or_404(Event.objects.select_related("organization"), pk=event_id)
    membership = membership_for(request.user, event.organization)
    if membership is None:
        from django.http import Http404

        raise Http404
    if not can(membership, "check_in", event):
        raise PermissionDenied
    return event


@login_required
def scanner(request, event_id):
    event = _event_for(request, event_id)
    return render(request, "checkin/scanner.html", {"event": event, "stats": stats(event)})


@login_required
@require_POST
def scan(request, event_id):
    """Accepts one scan or a batch of scans saved while offline."""
    event = _event_for(request, event_id)
    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"error": "Bad request"}, status=400)
    items = payload.get("scans") or [payload]
    results = []
    for item in items[:200]:
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        record = check_in(
            event,
            request.user,
            code=code,
            lane=str(item.get("lane") or ""),
            device_id=str(item.get("device_id") or ""),
            client_scan_id=str(item.get("client_scan_id") or "") or None,
            scanned_at=item.get("scanned_at"),
            was_offline=bool(item.get("offline")),
        )
        result = describe(record, event)
        result["client_scan_id"] = item.get("client_scan_id")
        results.append(result)
    return JsonResponse({"results": results, "stats": stats(event)})


@login_required
def search(request, event_id):
    """CHK-04: find someone by name or order when their QR won't scan."""
    event = _event_for(request, event_id)
    lane = request.GET.get("lane") or request.POST.get("lane") or ""
    message = None
    if request.method == "POST":
        ticket = get_object_or_404(Ticket, pk=request.POST.get("ticket"), event=event)
        record = check_in(event, request.user, ticket=ticket, lane=lane, method=CheckInEvent.Method.SEARCH,
                          client_scan_id=request.POST.get("client_scan_id") or None)
        message = describe(record, event)
    query = (request.GET.get("q") or request.POST.get("q") or "").strip()
    matches = []
    if len(query) >= 2:
        matches = (
            Attendee.objects.filter(order__event=event, ticket__isnull=False)
            .filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(order__number__icontains=query)
                    | Q(ticket__display_id__icontains=query))
            .select_related("ticket", "ticket_type", "ticket__checked_in_by")
            .order_by("last_name", "first_name")[:25]
        )
    return render(
        request,
        "checkin/search.html",
        {"event": event, "query": query, "matches": matches, "message": message, "lane": lane, "stats": stats(event)},
    )
