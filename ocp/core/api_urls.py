from django.urls import path
from ocp.accounts import api as accounts
from ocp.events import api as events
from ocp.ticketing import api as ticketing
from ocp.comms import api as comms
from ocp.reports import api as reports

E = "organizations/<slug:org_slug>/events/<int:event_id>/"
urlpatterns = [
    path("session/", accounts.session),
    path("auth/login/", accounts.sign_in),
    path("auth/logout/", accounts.sign_out),
    path("events/", events.public_events),
    path("events/<slug:slug>/", events.public_event),
    path("organizations/<slug:org_slug>/events/", events.organization_events),
    path(E + "dashboard/", reports.dashboard),
    path(E + "orders/", ticketing.orders),
    path(E + "attendees/", ticketing.attendees),
    path(E + "communications/", comms.communications),
]
