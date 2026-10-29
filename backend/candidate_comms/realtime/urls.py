from django.urls import path

from .views import event_stream_view

urlpatterns = [
    path("", event_stream_view, name="event-stream"),
]
