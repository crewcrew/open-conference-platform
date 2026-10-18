from django.urls import path

from . import views

app_name = "checkin"

urlpatterns = [
    path("<int:event_id>/", views.scanner, name="scanner"),
    path("<int:event_id>/scan/", views.scan, name="scan"),
    path("<int:event_id>/search/", views.search, name="search"),
]
