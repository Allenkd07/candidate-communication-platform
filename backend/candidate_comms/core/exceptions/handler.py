"""Renders every API error as {"error": {"code", "message", "fields"}}."""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

from .codes import ErrorCode
from .errors import ApplicationError

logger = logging.getLogger(__name__)

# Error code per DRF exception class; unmapped classes are resolved from the HTTP status.
_DRF_CODES: dict[type[exceptions.APIException], ErrorCode] = {
    exceptions.ValidationError: ErrorCode.VALIDATION_ERROR,
    exceptions.ParseError: ErrorCode.PARSE_ERROR,
    exceptions.NotAuthenticated: ErrorCode.NOT_AUTHENTICATED,
    exceptions.AuthenticationFailed: ErrorCode.NOT_AUTHENTICATED,
    exceptions.PermissionDenied: ErrorCode.PERMISSION_DENIED,
    exceptions.NotFound: ErrorCode.NOT_FOUND,
    exceptions.MethodNotAllowed: ErrorCode.METHOD_NOT_ALLOWED,
    exceptions.NotAcceptable: ErrorCode.NOT_ACCEPTABLE,
    exceptions.UnsupportedMediaType: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
    exceptions.Throttled: ErrorCode.THROTTLED,
}

_STATUS_CODES: dict[int, ErrorCode] = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.NOT_AUTHENTICATED,
    403: ErrorCode.PERMISSION_DENIED,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    429: ErrorCode.THROTTLED,
}

VALIDATION_MESSAGE = "Some fields are invalid."
INTERNAL_MESSAGE = "Something went wrong on our side. Please try again."


def error_body(
    code: ErrorCode, message: str, fields: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "fields": fields or {}}}


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    if isinstance(exc, ApplicationError):
        set_rollback()  # Roll back an atomic request's writes, matching DRF's own exceptions.
        body = error_body(exc.code, exc.message, exc.fields)
        return Response(body, status=exc.status_code)

    # Convert Django exceptions (get_object_or_404, model validation) to their DRF equivalents.
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    # The DRF handler builds the response with the Allow, Retry-After and WWW-Authenticate headers.
    response = drf_exception_handler(exc, context)
    if response is None or not isinstance(exc, exceptions.APIException):
        logger.exception("Unhandled API error", exc_info=exc)
        # Returning a response marks the error as handled, so undo the request's writes here.
        set_rollback()
        body = error_body(ErrorCode.INTERNAL_ERROR, INTERNAL_MESSAGE)
        return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if isinstance(exc, exceptions.ValidationError):
        fields = _flatten(exc.detail)
        # Field-independent errors (non_field_errors, or "" from a bare string) become the message.
        general = fields.pop("non_field_errors", []) + fields.pop("", [])
        message = _first(general) or VALIDATION_MESSAGE
        response.data = error_body(ErrorCode.VALIDATION_ERROR, message, fields)
    else:
        messages = [message for group in _flatten(exc.detail).values() for message in group]
        message = _first(messages) or str(exc.default_detail)
        response.data = error_body(_code_for(exc), message)
    return response


def _code_for(exc: exceptions.APIException) -> ErrorCode:
    for exc_type in type(exc).__mro__:
        if exc_type in _DRF_CODES:
            return _DRF_CODES[exc_type]
    # Custom APIException subclasses: classify by status so a client error is never
    # reported as a server fault.
    if exc.status_code in _STATUS_CODES:
        return _STATUS_CODES[exc.status_code]
    return ErrorCode.BAD_REQUEST if exc.status_code < 500 else ErrorCode.INTERNAL_ERROR


def _flatten(detail: Any, prefix: str = "") -> dict[str, list[str]]:
    """Turn DRF's nested error detail into {"field.sub.0": ["message", ...]}."""
    if isinstance(detail, dict):
        flat: dict[str, list[str]] = {}
        for key, value in detail.items():
            flat.update(_flatten(value, f"{prefix}.{key}" if prefix else str(key)))
        return flat
    if isinstance(detail, list) and any(isinstance(item, dict | list) for item in detail):
        flat = {}
        for index, value in enumerate(detail):
            flat.update(_flatten(value, f"{prefix}.{index}" if prefix else str(index)))
        return flat
    messages = detail if isinstance(detail, list) else [detail]
    return {prefix: [str(message) for message in messages if str(message)]}


def _first(messages: list[str] | None) -> str | None:
    return messages[0] if messages else None
