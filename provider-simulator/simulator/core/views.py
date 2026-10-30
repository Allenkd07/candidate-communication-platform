"""Django-level 404/500 handlers, so unmatched URLs also answer with the error envelope."""

from django.http import HttpRequest, HttpResponse, JsonResponse

from .errors import ErrorCode, error_body


def page_not_found(request: HttpRequest, exception: Exception | None) -> HttpResponse:
    return JsonResponse(error_body(ErrorCode.NOT_FOUND, "Not found."), status=404)


def server_error(request: HttpRequest) -> HttpResponse:
    body = error_body(ErrorCode.INTERNAL_ERROR, "Internal provider error.")
    return JsonResponse(body, status=500)
