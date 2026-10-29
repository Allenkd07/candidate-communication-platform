from typing import Any

from django.db.models import Model, QuerySet
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def paginated_response[M: Model](
    *,
    queryset: QuerySet[M],
    serializer_class: type[serializers.BaseSerializer[Any]],
    request: Request,
    view: APIView,
) -> Response:
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)
    serializer = serializer_class(page, many=True)
    return paginator.get_paginated_response(serializer.data)


def paginated_serializer(
    child: type[serializers.BaseSerializer[Any]], *, name: str
) -> type[serializers.Serializer[Any]]:
    """Schema-only serializer describing a StandardPagination page of `child` items."""
    fields: dict[str, Any] = {
        "count": serializers.IntegerField(),
        "next": serializers.URLField(allow_null=True),
        "previous": serializers.URLField(allow_null=True),
        "results": child(many=True),
    }
    return type(name, (serializers.Serializer,), fields)
