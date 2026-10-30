"""Provider errors, rendered as {"error": {"code", "message"}} like a real messaging vendor."""

import logging
from enum import StrEnum
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    """Codes the platform's adapter maps to its own gateway errors."""

    INVALID_REQUEST = "invalid_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    IDEMPOTENCY_KEY_REUSED = "idempotency_key_reused"
    INVALID_RECIPIENT = "invalid_recipient"
    RATE_LIMITED = "rate_limited"
    GATEWAY_UNAVAILABLE = "gateway_unavailable"
    INTERNAL_ERROR = "internal_error"


class ProviderError(Exception):
    """A deliberate provider response: a validation failure, a test number or an injected fault."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode,
        status_code: int,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.headers = headers or {}


_DRF_CODES: dict[type[exceptions.APIException], ErrorCode] = {
    exceptions.NotAuthenticated: ErrorCode.UNAUTHORIZED,
    exceptions.AuthenticationFailed: ErrorCode.UNAUTHORIZED,
    exceptions.PermissionDenied: ErrorCode.FORBIDDEN,
    exceptions.NotFound: ErrorCode.NOT_FOUND,
    exceptions.MethodNotAllowed: ErrorCode.METHOD_NOT_ALLOWED,
    exceptions.Throttled: ErrorCode.RATE_LIMITED,
}


def error_body(code: ErrorCode, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    if isinstance(exc, ProviderError):
        set_rollback()
        return Response(
            error_body(exc.code, exc.message), status=exc.status_code, headers=exc.headers
        )
    # Convert Django exceptions to their DRF equivalents so they keep their status code.
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None or not isinstance(exc, exceptions.APIException):
        logger.exception("Unhandled provider error", exc_info=exc)
        set_rollback()
        return Response(
            error_body(ErrorCode.INTERNAL_ERROR, "Internal provider error."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = next(
        (_DRF_CODES[cls] for cls in type(exc).__mro__ if cls in _DRF_CODES),
        ErrorCode.INVALID_REQUEST,
    )
    response.data = error_body(code, _first_message(exc.detail) or str(exc.default_detail))
    return response


def _first_message(detail: Any, field: str = "") -> str | None:
    """The first error in DRF's nested detail, prefixed with its field, e.g. "body: Required."."""
    if isinstance(detail, dict):
        for key, value in detail.items():
            name = "" if key == "non_field_errors" else str(key)
            message = _first_message(value, f"{field}.{name}" if field and name else field or name)
            if message:
                return message
        return None
    if isinstance(detail, list):
        for item in detail:
            message = _first_message(item, field)
            if message:
                return message
        return None
    text = str(detail)
    if not text:
        return None
    return f"{field}: {text}" if field else text
