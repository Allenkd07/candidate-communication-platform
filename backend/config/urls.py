from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import URLPattern, URLResolver, include, path

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/", include("candidate_comms.api.urls")),
]

if settings.DEBUG:
    # uvicorn doesn't serve static files; in dev Django does it (admin, browsable API)
    urlpatterns += staticfiles_urlpatterns()
