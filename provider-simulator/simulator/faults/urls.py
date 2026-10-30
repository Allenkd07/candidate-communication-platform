from django.urls import path

from .views import FaultsApi

urlpatterns = [
    path("faults", FaultsApi.as_view(), name="faults"),
]
