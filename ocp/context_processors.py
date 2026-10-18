from django.conf import settings


def site(request):
    return {
        "platform_name": settings.OCP_SITE_NAME,
        "google_fonts": settings.OCP_GOOGLE_FONTS,
    }
