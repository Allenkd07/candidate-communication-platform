from django.urls import path

from .views import BatchDetailApi, CandidateMessageHistoryApi, MessageSendApi

urlpatterns = [
    path("messages/", MessageSendApi.as_view(), name="message-send"),
    path("batches/<uuid:batch_id>/", BatchDetailApi.as_view(), name="batch-detail"),
    path(
        "candidates/<uuid:candidate_id>/messages/",
        CandidateMessageHistoryApi.as_view(),
        name="candidate-message-history",
    ),
]
