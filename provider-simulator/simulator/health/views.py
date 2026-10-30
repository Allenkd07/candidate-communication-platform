from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from simulator.faults.services import health_status


class HealthApi(APIView):
    # Public, like a vendor's status page.
    authentication_classes = ()
    permission_classes = ()

    def get(self, request: Request) -> Response:
        return Response({"status": health_status()})


class ServiceIndexApi(APIView):
    """What this service is and where its endpoints are, for anyone opening the base URL."""

    authentication_classes = ()
    permission_classes = ()

    def get(self, request: Request) -> Response:
        return Response(
            {
                "service": "Provider simulator",
                "description": (
                    "A stand-in SMS provider for the Candidate Communication Platform. "
                    "The platform sends messages here and receives signed delivery webhooks."
                ),
                "endpoints": {
                    "health": "GET /health",
                    "send": "POST /v1/messages (API key)",
                    "status": "GET /v1/messages/{id} (API key)",
                    "faults": "GET, POST /_demo/faults (API key)",
                },
            }
        )
