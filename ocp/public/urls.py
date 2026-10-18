from django.urls import path

from . import views

app_name = "public"

urlpatterns = [
    path("", views.home, name="home"),
    path("e/<slug:slug>/", views.event_page, name="event"),
    path("e/<slug:slug>/calendar.ics", views.calendar, name="calendar"),
    path("checkout/<str:token>/", views.checkout_page, name="checkout"),
    path("checkout/<str:token>/cancel/", views.checkout_cancel, name="checkout_cancel"),
    path("pay/test/<str:ref>/", views.test_payment, name="test_payment"),
    path("payments/webhook/<str:provider>/", views.payment_webhook, name="payment_webhook"),
    path("booking/", views.booking_lookup, name="booking_lookup"),
    path("booking/<str:token>/", views.booking, name="booking"),
    path("t/<str:code>/", views.ticket, name="ticket"),
    path("unsubscribe/<str:token>/", views.unsubscribe, name="unsubscribe"),
]
