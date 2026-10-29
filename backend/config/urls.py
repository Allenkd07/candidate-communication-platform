from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import URLPattern, URLResolver, include, path

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/", include("candidate_comms.api.urls")),
]

handler404 = "candidate_comms.core.exceptions.views.page_not_found"
handler500 = "candidate_comms.core.exceptions.views.server_error"

if settings.DEBUG:
    # uvicorn does not serve static files, so Django serves them when DEBUG is on.
    urlpatterns += staticfiles_urlpatterns()
