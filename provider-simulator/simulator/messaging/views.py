from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from simulator.faults.services import faults_apply

from .serializers import (
    MessageAcceptedSerializer,
    MessageOutputSerializer,
    MessageSendInputSerializer,
)
from .services import message_get, message_send


class MessageSendApi(APIView):
    def post(self, request: Request) -> Response:
        faults_apply()
        serializer = MessageSendInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        outcome = message_send(**serializer.validated_data)
        headers = {"Idempotent-Replayed": "true"} if outcome.replayed else None
        return Response(
            MessageAcceptedSerializer(outcome.message).data,
            status=status.HTTP_202_ACCEPTED,
            headers=headers,
        )


class MessageDetailApi(APIView):
    def get(self, request: Request, message_id: str) -> Response:
        faults_apply()
        return Response(MessageOutputSerializer(message_get(message_id=message_id)).data)
