from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from candidate_comms.core.pagination import paginated_response

from .selectors import (
    batch_summary,
    candidate_message_history,
    service_health,
    template_get,
    template_list,
)
from .serializers import (
    BatchOutputSerializer,
    MessageOutputSerializer,
    MessagePageSerializer,
    MessageSendInputSerializer,
    ServiceHealthSerializer,
    TemplateInputSerializer,
    TemplateOutputSerializer,
)
from .services.dispatch import batch_create
from .services.retry import batch_retry_failed, message_retry
from .services.templates import template_create, template_delete, template_update

_TAGS = ["messages"]


class MessageSendApi(APIView):
    @extend_schema(
        operation_id="messages_send",
        request=MessageSendInputSerializer,
        responses={202: BatchOutputSerializer},
        tags=_TAGS,
        description=(
            "Queue one message per candidate. Returns 202 with every recipient, normally still "
            "QUEUED; statuses then change asynchronously (follow them via the events stream)."
        ),
    )
    def post(self, request: Request) -> Response:
        serializer = MessageSendInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = batch_create(**serializer.validated_data)
        data = BatchOutputSerializer(batch_summary(batch_id=batch.id)).data
        return Response(data, status=status.HTTP_202_ACCEPTED)


class BatchDetailApi(APIView):
    @extend_schema(operation_id="batches_retrieve", responses=BatchOutputSerializer, tags=_TAGS)
    def get(self, request: Request, batch_id: UUID) -> Response:
        return Response(BatchOutputSerializer(batch_summary(batch_id=batch_id)).data)


class MessageRetryApi(APIView):
    @extend_schema(
        operation_id="messages_retry",
        request=None,
        responses={202: BatchOutputSerializer},
        tags=_TAGS,
        description=(
            "Send a failed message again as a new message in the same batch. Returns the batch, "
            "in which the retry replaces the failed message. 409 not_retryable when the failure "
            "doesn't allow a retry, it was already retried, or the candidate was deleted."
        ),
    )
    def post(self, request: Request, message_id: UUID) -> Response:
        retry = message_retry(message_id=message_id)
        data = BatchOutputSerializer(batch_summary(batch_id=retry.batch_id)).data
        return Response(data, status=status.HTTP_202_ACCEPTED)


class BatchRetryFailedApi(APIView):
    @extend_schema(
        operation_id="batches_retry_failed",
        request=None,
        responses={202: BatchOutputSerializer},
        tags=_TAGS,
        description="Send every retryable failed message of a batch again; 409 if there are none.",
    )
    def post(self, request: Request, batch_id: UUID) -> Response:
        batch_retry_failed(batch_id=batch_id)
        data = BatchOutputSerializer(batch_summary(batch_id=batch_id)).data
        return Response(data, status=status.HTTP_202_ACCEPTED)


class ServiceHealthApi(APIView):
    @extend_schema(
        operation_id="providers_health",
        responses=ServiceHealthSerializer,
        tags=_TAGS,
        description=(
            "Whether each messaging provider is reachable (operational, degraded or down) and "
            "its message counts over the last 24 hours."
        ),
    )
    def get(self, request: Request) -> Response:
        return Response(ServiceHealthSerializer(service_health()).data)


class TemplateListCreateApi(APIView):
    @extend_schema(
        operation_id="templates_list",
        responses=TemplateOutputSerializer(many=True),
        tags=["templates"],
    )
    def get(self, request: Request) -> Response:
        return Response(TemplateOutputSerializer(template_list(), many=True).data)

    @extend_schema(
        operation_id="templates_create",
        request=TemplateInputSerializer,
        responses={201: TemplateOutputSerializer},
        tags=["templates"],
    )
    def post(self, request: Request) -> Response:
        serializer = TemplateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = template_create(**serializer.validated_data)
        return Response(TemplateOutputSerializer(template).data, status=status.HTTP_201_CREATED)


class TemplateDetailApi(APIView):
    @extend_schema(
        operation_id="templates_update",
        request=TemplateInputSerializer,
        responses=TemplateOutputSerializer,
        tags=["templates"],
    )
    def put(self, request: Request, template_id: UUID) -> Response:
        serializer = TemplateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = template_update(
            template=template_get(template_id=template_id), **serializer.validated_data
        )
        return Response(TemplateOutputSerializer(template).data)

    @extend_schema(operation_id="templates_delete", responses={204: None}, tags=["templates"])
    def delete(self, request: Request, template_id: UUID) -> Response:
        template_delete(template=template_get(template_id=template_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateMessageHistoryApi(APIView):
    @extend_schema(
        operation_id="candidates_messages_list",
        parameters=[
            OpenApiParameter("page", int, description="1-based page number"),
            OpenApiParameter("page_size", int, description="Items per page, at most 100"),
        ],
        responses=MessagePageSerializer,
        tags=_TAGS,
    )
    def get(self, request: Request, candidate_id: UUID) -> Response:
        return paginated_response(
            queryset=candidate_message_history(candidate_id=candidate_id),
            serializer_class=MessageOutputSerializer,
            request=request,
            view=self,
        )
