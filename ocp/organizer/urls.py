from django.urls import path

from ocp.accounts import views as account
from ocp.comms import views as comms
from ocp.events import views as events
from ocp.ticketing import views as people
from ocp.reports import views as reports

app_name = "organizer"

E = "<slug:org_slug>/e/<int:event_id>/"

urlpatterns = [
    path("", account.home, name="home"),
    path("new/", account.org_create, name="org_create"),
    path("<slug:org_slug>/", account.org_home, name="org"),
    path("<slug:org_slug>/check-in/", account.volunteer_home, name="volunteer"),
    path("<slug:org_slug>/settings/", account.org_settings, name="org_settings"),
    path("<slug:org_slug>/team/", account.team, name="team"),
    path("<slug:org_slug>/team/<int:member_id>/", account.member_edit, name="member_edit"),
    path("<slug:org_slug>/team/invites/<int:invite_id>/withdraw/", account.invite_revoke, name="invite_revoke"),
    path("<slug:org_slug>/events/new/", events.event_create, name="event_create"),
    path(E, reports.dashboard, name="dashboard"),
    path(E + "edit/", events.event_edit, name="event_edit"),
    path(E + "status/", events.event_status, name="event_status"),
    path(E + "duplicate/", events.event_duplicate, name="event_duplicate"),
    path(E + "sessions/", events.sessions, name="sessions"),
    path(E + "tickets/", events.tickets, name="tickets"),
    path(E + "questions/", events.questions, name="questions"),
    path(E + "coupons/", events.coupons, name="coupons"),
    path(E + "orders/", people.orders, name="orders"),
    path(E + "orders/<int:order_id>/", people.order_detail, name="order_detail"),
    path(E + "attendees/", people.attendees, name="attendees"),
    path(E + "attendees/<int:attendee_id>/edit/", people.attendee_edit, name="attendee_edit"),
    path(E + "attendees/<int:attendee_id>/resend/", people.attendee_resend, name="attendee_resend"),
    path(E + "attendees/<int:attendee_id>/check-in/", people.manual_check_in, name="manual_check_in"),
    path(E + "deliveries/<int:delivery_id>/retry/", people.delivery_retry, name="delivery_retry"),
    path(E + "emails/", comms.emails, name="emails"),
    path(E + "emails/new/", comms.compose, name="compose"),
    path(E + "emails/<int:communication_id>/", comms.email_detail, name="email_detail"),
    path(E + "reports/", reports.reports, name="reports"),
    path(E + "history/", reports.history, name="history"),
]
