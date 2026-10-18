import json
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET, require_POST
from .forms import EmailLoginForm


def _session_response(request):
    user = request.user
    memberships = []
    if user.is_authenticated:
        memberships = [{"slug": m.organization.slug, "name": m.organization.name, "role": m.role}
                       for m in user.memberships.select_related("organization")]
    return JsonResponse({"authenticated": user.is_authenticated, "csrf_token": get_token(request),
                         "user": {"name": user.get_full_name(), "email": user.email} if user.is_authenticated else None,
                         "organizations": memberships})


@require_GET
def session(request):
    return _session_response(request)


@require_POST
def sign_in(request):
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid_json"}, status=400)
    if not isinstance(data.get("email"), str) or not isinstance(data.get("password"), str):
        return JsonResponse({"error": "invalid_credentials"}, status=400)
    form = EmailLoginForm(request=request, data={"username": data["email"], "password": data["password"]})
    if not form.is_valid():
        return JsonResponse({"error": "invalid_credentials"}, status=400)
    login(request, form.get_user())
    return _session_response(request)


@require_POST
def sign_out(request):
    logout(request)
    return JsonResponse({"ok": True})
