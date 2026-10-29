from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

v1_patterns: list[URLPattern | URLResolver] = []

urlpatterns = [
    path("v1/", include((v1_patterns, "v1"))),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
