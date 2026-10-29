from django.urls import path

from .views import CandidateBulkDeleteApi, CandidateDetailApi, CandidateListCreateApi

urlpatterns = [
    path("", CandidateListCreateApi.as_view(), name="candidate-list"),
    path("bulk-delete/", CandidateBulkDeleteApi.as_view(), name="candidate-bulk-delete"),
    path("<uuid:candidate_id>/", CandidateDetailApi.as_view(), name="candidate-detail"),
]
