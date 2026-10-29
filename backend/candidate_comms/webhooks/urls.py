from django.urls import path

from .views import WebhookIngestApi

urlpatterns = [
    path("<slug:gateway>/", WebhookIngestApi.as_view(), name="webhook-ingest"),
]
