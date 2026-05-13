from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok", "service": "eld-backend"})


urlpatterns = [
    path("", health, name="root"),
    path("healthz/", health, name="healthz"),
    path("admin/", admin.site.urls),
    path("api/", include("trips.urls")),
]
