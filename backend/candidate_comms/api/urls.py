from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

v1_patterns: list[URLPattern | URLResolver] = [
    path("candidates/", include("candidate_comms.candidates.urls")),
    path("", include("candidate_comms.communications.urls")),
    path("webhooks/", include("candidate_comms.webhooks.urls")),
    path("events/", include("candidate_comms.realtime.urls")),
]

urlpatterns = [
    path("v1/", include((v1_patterns, "v1"))),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
