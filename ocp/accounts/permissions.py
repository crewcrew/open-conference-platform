"""Role-based access (ORG-04, ORG-05, CHK-05).

Every organizer view resolves the organization from the URL and the person's
membership in it. A person with no membership gets a 404, so other
organizations' events are never revealed.
"""

from .models import Role

OWNER, ADMIN, MANAGER, VOLUNTEER = Role.OWNER, Role.ADMIN, Role.EVENT_MANAGER, Role.VOLUNTEER

CAPABILITIES = {
    "manage_org": {OWNER},
    "manage_team": {OWNER, ADMIN},
    "manage_events": {OWNER, ADMIN, MANAGER},
    "view_attendees": {OWNER, ADMIN, MANAGER},
    "edit_attendees": {OWNER, ADMIN, MANAGER},
    "send_comms": {OWNER, ADMIN, MANAGER},
    "view_reports": {OWNER, ADMIN, MANAGER},
    "refund": {OWNER, ADMIN},
    "check_in": {OWNER, ADMIN, MANAGER, VOLUNTEER},
}


def membership_for(user, organization):
    if not user.is_authenticated:
        return None
    return user.memberships.filter(organization=organization).first()


def can(membership, capability, event=None):
    if membership is None:
        return False
    if membership.role not in CAPABILITIES[capability]:
        return False
    if membership.role == VOLUNTEER and event is not None:
        return membership.events.filter(pk=event.pk).exists()
    return True


def capabilities_for(membership, event=None):
    return {name for name in CAPABILITIES if can(membership, name, event)}
