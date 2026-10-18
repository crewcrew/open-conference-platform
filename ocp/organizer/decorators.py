from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ocp.accounts.models import Organization
from ocp.accounts.permissions import can, capabilities_for, membership_for
from ocp.events.models import Event


def organizer_view(capability=None):
    """Resolve the organization (and event) from the URL and check the role.

    People outside the organization get a 404 so its events aren't revealed.
    Event pages run in the event's time zone, so form inputs and dates mean
    local event time (EVT-07).
    """

    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, org_slug, *args, **kwargs):
            organization = get_object_or_404(Organization, slug=org_slug)
            membership = membership_for(request.user, organization)
            if membership is None:
                raise Http404
            event = None
            if "event_id" in kwargs:
                event = get_object_or_404(Event, pk=kwargs.pop("event_id"), organization=organization)
            if capability and not can(membership, capability, event):
                raise PermissionDenied
            request.org = organization
            request.membership = membership
            request.event = event
            request.caps = capabilities_for(membership, event)
            if event is not None:
                with timezone.override(event.tz):
                    return view(request, *args, **kwargs)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
