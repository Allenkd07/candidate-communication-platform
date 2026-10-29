from django.urls import path

from .views import HealthApi

urlpatterns = [
    path("", HealthApi.as_view(), name="health"),
]
