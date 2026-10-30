from django.urls import URLPattern, URLResolver, include, path, re_path

from simulator.core.views import page_not_found

urlpatterns: list[URLPattern | URLResolver] = [
    path("health", include("simulator.health.urls")),
    path("v1/", include("simulator.messaging.urls")),
    # Demo control for fault injection; not part of a real vendor's API, hence the _demo prefix.
    path("_demo/", include("simulator.faults.urls")),
    # Catch-all: unmatched URLs get the JSON error envelope even with DEBUG on, where Django
    # would otherwise render its HTML 404 page.
    re_path(r"^", page_not_found, {"exception": None}),
]

handler404 = "simulator.core.views.page_not_found"
handler500 = "simulator.core.views.server_error"
