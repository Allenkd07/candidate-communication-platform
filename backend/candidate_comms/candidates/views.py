from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from candidate_comms.core.pagination import paginated_response

from .selectors import CandidateFilters, candidate_get, candidate_list
from .serializers import (
    CandidateBulkDeleteInputSerializer,
    CandidateBulkDeleteOutputSerializer,
    CandidateCreateInputSerializer,
    CandidateListFilterSerializer,
    CandidateListOutputSerializer,
    CandidateOutputSerializer,
    CandidatePageSerializer,
)
from .services import candidate_create, candidate_delete, candidates_bulk_delete

_TAGS = ["candidates"]


class CandidateListCreateApi(APIView):
    @extend_schema(
        operation_id="candidates_list",
        parameters=[
            CandidateListFilterSerializer,
            OpenApiParameter("page", int, description="1-based page number"),
            OpenApiParameter("page_size", int, description="Items per page, at most 100"),
        ],
        responses=CandidatePageSerializer,
        tags=_TAGS,
    )
    def get(self, request: Request) -> Response:
        filters = CandidateListFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        data = filters.validated_data
        queryset = candidate_list(
            search=data["search"],
            filters=CandidateFilters(
                name=data["name"],
                phone=data["phone"],
                code=data["code"],
                statuses=data["status"],
                last_message_after=data["last_message_after"],
                last_message_before=data["last_message_before"],
            ),
            sort=data["sort"],
        )
        return paginated_response(
            queryset=queryset,
            serializer_class=CandidateListOutputSerializer,
            request=request,
            view=self,
        )

    @extend_schema(
        operation_id="candidates_create",
        request=CandidateCreateInputSerializer,
        responses={201: CandidateOutputSerializer},
        tags=_TAGS,
    )
    def post(self, request: Request) -> Response:
        serializer = CandidateCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = candidate_create(**serializer.validated_data)
        return Response(CandidateOutputSerializer(candidate).data, status=status.HTTP_201_CREATED)


class CandidateDetailApi(APIView):
    @extend_schema(
        operation_id="candidates_retrieve", responses=CandidateOutputSerializer, tags=_TAGS
    )
    def get(self, request: Request, candidate_id: UUID) -> Response:
        candidate = candidate_get(candidate_id=candidate_id)
        return Response(CandidateOutputSerializer(candidate).data)

    @extend_schema(operation_id="candidates_destroy", responses={204: None}, tags=_TAGS)
    def delete(self, request: Request, candidate_id: UUID) -> Response:
        candidate_delete(candidate=candidate_get(candidate_id=candidate_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateBulkDeleteApi(APIView):
    @extend_schema(
        operation_id="candidates_bulk_delete",
        request=CandidateBulkDeleteInputSerializer,
        responses=CandidateBulkDeleteOutputSerializer,
        tags=_TAGS,
    )
    def post(self, request: Request) -> Response:
        serializer = CandidateBulkDeleteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deleted = candidates_bulk_delete(candidate_ids=serializer.validated_data["candidate_ids"])
        return Response(CandidateBulkDeleteOutputSerializer({"deleted": deleted}).data)
