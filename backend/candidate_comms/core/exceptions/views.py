"""Django-level 404/500 handlers, so unmatched /api/ URLs also answer with the error envelope."""

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import defaults

from .codes import ErrorCode
from .handler import INTERNAL_MESSAGE, error_body


def _is_api(request: HttpRequest) -> bool:
    return request.path.startswith("/api/")


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    if _is_api(request):
        body = error_body(ErrorCode.NOT_FOUND, "Not found.")
        return JsonResponse(body, status=404)
    return defaults.page_not_found(request, exception)


def server_error(request: HttpRequest) -> HttpResponse:
    if _is_api(request):
        return JsonResponse(error_body(ErrorCode.INTERNAL_ERROR, INTERNAL_MESSAGE), status=500)
    return defaults.server_error(request)
