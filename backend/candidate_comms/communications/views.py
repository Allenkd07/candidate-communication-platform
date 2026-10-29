from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from candidate_comms.core.pagination import paginated_response

from .selectors import batch_summary, candidate_message_history
from .serializers import (
    BatchOutputSerializer,
    MessageOutputSerializer,
    MessagePageSerializer,
    MessageSendInputSerializer,
)
from .services.dispatch import batch_create

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
