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
