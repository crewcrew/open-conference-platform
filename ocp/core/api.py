"""Shared API authentication and pagination. Business rules stay in feature services."""
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from ocp.accounts.models import Organization
from ocp.accounts.permissions import membership_for, can
from ocp.events.models import Event


def event_access(capability):
    def decorate(view):
        @wraps(view)
        def wrapped(request, org_slug, event_id, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"error": "authentication_required"}, status=401)
            org = get_object_or_404(Organization, slug=org_slug)
            member = membership_for(request.user, org)
            if member is None:
                return JsonResponse({"error": "not_found"}, status=404)
            event = get_object_or_404(Event, pk=event_id, organization=org)
            if not can(member, capability, event):
                return JsonResponse({"error": "forbidden"}, status=403)
            return view(request, event, member, *args, **kwargs)
        return wrapped
    return decorate


def paginated(request, rows):
    try:
        page = max(1, int(request.GET.get("page", "1")))
    except ValueError:
        return JsonResponse({"error": "invalid_page"}, status=400)
    count = rows.count()
    return JsonResponse({"results": list(rows[(page-1)*50:page*50]), "count": count,
                         "page": page, "page_size": 50, "has_next": page*50 < count})
