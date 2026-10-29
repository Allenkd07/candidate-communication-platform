from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import webhook_ingest


class WebhookIngestOutputSerializer(serializers.Serializer[object]):
    received = serializers.IntegerField()
    applied = serializers.IntegerField()
    ignored = serializers.IntegerField()


class WebhookIngestApi(APIView):
    # Gateways authenticate with a request signature, not with user credentials.
    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        operation_id="webhooks_ingest",
        request=None,
        responses={
            200: WebhookIngestOutputSerializer,
            400: OpenApiResponse(description="Malformed payload"),
            401: OpenApiResponse(description="Invalid signature"),
            404: OpenApiResponse(description="Unknown gateway"),
        },
        tags=["webhooks"],
    )
    def post(self, request: Request, gateway: str) -> Response:
        # request.body, not request.data: the signature covers the exact raw bytes.
        result = webhook_ingest(gateway_name=gateway, headers=request.headers, body=request.body)
        data = WebhookIngestOutputSerializer(result).data
        return Response(data, status=status.HTTP_200_OK)
