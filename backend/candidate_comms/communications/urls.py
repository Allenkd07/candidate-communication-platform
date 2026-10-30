from django.urls import path

from .views import (
    BatchDetailApi,
    BatchRetryFailedApi,
    CandidateMessageHistoryApi,
    MessageRetryApi,
    MessageSendApi,
    ServiceHealthApi,
    TemplateDetailApi,
    TemplateListCreateApi,
)

urlpatterns = [
    path("messages/", MessageSendApi.as_view(), name="message-send"),
    path("messages/<uuid:message_id>/retry/", MessageRetryApi.as_view(), name="message-retry"),
    path("batches/<uuid:batch_id>/", BatchDetailApi.as_view(), name="batch-detail"),
    path("providers/health/", ServiceHealthApi.as_view(), name="providers-health"),
    path("templates/", TemplateListCreateApi.as_view(), name="template-list"),
    path("templates/<uuid:template_id>/", TemplateDetailApi.as_view(), name="template-detail"),
    path(
        "batches/<uuid:batch_id>/retry-failed/",
        BatchRetryFailedApi.as_view(),
        name="batch-retry-failed",
    ),
    path(
        "candidates/<uuid:candidate_id>/messages/",
        CandidateMessageHistoryApi.as_view(),
        name="candidate-message-history",
    ),
]
