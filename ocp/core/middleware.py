"""Credentialed CORS restricted to explicitly configured frontend origins."""
from django.conf import settings
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers


class FrontendCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        is_api = request.path.startswith("/api/v1/")
        allowed = is_api and origin in settings.OCP_FRONTEND_ORIGINS
        if is_api and request.method == "OPTIONS":
            response = HttpResponse(status=204 if allowed else 403)
        else:
            response = self.get_response(request)
        if is_api:
            response["Cache-Control"] = "no-store"
            patch_vary_headers(response, ("Origin", "Cookie"))
        if allowed:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
        return response
