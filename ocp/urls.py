from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from ocp.accounts import views as views_account
from ocp.accounts.forms import EmailLoginForm

from ocp.core import health

urlpatterns = [
    path("health/live/", health.live),
    path("health/ready/", health.ready),
    path("api/v1/", include("ocp.core.api_urls")),
    path("", include("ocp.public.urls")),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(authentication_form=EmailLoginForm, redirect_authenticated_user=True),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", views_account.signup, name="signup"),
    path("accounts/password/", auth_views.PasswordChangeView.as_view(success_url="/manage/"), name="password_change"),
    path("invite/<str:token>/", views_account.accept_invite, name="accept_invite"),
    path("manage/", include("ocp.organizer.urls")),
    path("checkin/", include("ocp.checkin.urls")),
    path("django-admin/", admin.site.urls),
]
