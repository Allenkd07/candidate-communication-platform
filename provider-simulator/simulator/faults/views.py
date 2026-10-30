from typing import Any

from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MAX_LATENCY_MS
from .services import faults_get, faults_update


class FaultsInputSerializer(serializers.Serializer[Any]):
    outage = serializers.BooleanField(required=False)
    failure_rate = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    latency_ms = serializers.IntegerField(required=False, min_value=0, max_value=MAX_LATENCY_MS)


class FaultsOutputSerializer(serializers.Serializer[Any]):
    outage = serializers.BooleanField()
    failure_rate = serializers.FloatField()
    latency_ms = serializers.IntegerField()
    updated_at = serializers.DateTimeField()


class FaultsApi(APIView):
    """Demo control: read or change the injected faults. Fields left out keep their value."""

    def get(self, request: Request) -> Response:
        return Response(FaultsOutputSerializer(faults_get()).data)

    def post(self, request: Request) -> Response:
        serializer = FaultsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = faults_update(**serializer.validated_data)
        return Response(FaultsOutputSerializer(config).data)
