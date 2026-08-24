from django.conf import settings


def store_info(request):
    return {
        "store_legal_name": settings.STORE_LEGAL_NAME,
        "site_url": settings.SITE_URL,
    }
