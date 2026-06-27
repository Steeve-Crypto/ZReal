from django.conf import settings


def frontend_origin(request):
    return {"FRONTEND_ORIGIN": settings.FRONTEND_ORIGIN.rstrip("/")}
