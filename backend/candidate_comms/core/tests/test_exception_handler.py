from typing import Any

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.test import Client
from rest_framework import exceptions, serializers

from candidate_comms.core.exceptions import ApplicationError, ErrorCode, handler
from candidate_comms.core.exceptions.handler import (
    INTERNAL_MESSAGE,
    VALIDATION_MESSAGE,
    api_exception_handler,
)


def handle(exc: Exception) -> tuple[int, dict[str, Any]]:
    response = api_exception_handler(exc, {})
    return response.status_code, response.data["error"]


class _NestedSerializer(serializers.Serializer[Any]):
    phone = serializers.CharField()


class _Serializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    items = _NestedSerializer(many=True)


def test_application_error_keeps_its_code_status_and_fields() -> None:
    exc = ApplicationError(
        "A candidate with this mobile number already exists.",
        code=ErrorCode.CONFLICT,
        status_code=409,
        fields={"phone": ["Already in use."]},
    )

    assert handle(exc) == (
        409,
        {
            "code": "conflict",
            "message": "A candidate with this mobile number already exists.",
            "fields": {"phone": ["Already in use."]},
        },
    )


def test_serializer_errors_are_flattened_into_fields() -> None:
    serializer = _Serializer(data={"email": "nope", "items": [{"phone": "1"}, {}]})
    assert not serializer.is_valid()

    status_code, error = handle(exceptions.ValidationError(serializer.errors))

    assert status_code == 400
    assert error["code"] == "validation_error"
    assert error["message"] == VALIDATION_MESSAGE
    assert error["fields"] == {
        "email": ["Enter a valid email address."],
        "items.1.phone": ["This field is required."],
    }


@pytest.mark.parametrize(
    "detail",
    [{"non_field_errors": ["Pick at least one candidate."]}, "Pick at least one candidate."],
)
def test_general_validation_error_becomes_the_message(detail: Any) -> None:
    status_code, error = handle(exceptions.ValidationError(detail))

    assert status_code == 400
    assert error == {
        "code": "validation_error",
        "message": "Pick at least one candidate.",
        "fields": {},
    }


def test_django_validation_error_is_converted() -> None:
    status_code, error = handle(DjangoValidationError({"email": ["Taken."]}))

    assert status_code == 400
    assert error["fields"] == {"email": ["Taken."]}


@pytest.mark.parametrize(
    ("exc", "status_code", "code"),
    [
        (Http404(), 404, ErrorCode.NOT_FOUND),
        (exceptions.NotFound(), 404, ErrorCode.NOT_FOUND),
        (exceptions.MethodNotAllowed("PUT"), 405, ErrorCode.METHOD_NOT_ALLOWED),
        (exceptions.ParseError(), 400, ErrorCode.PARSE_ERROR),
        (exceptions.UnsupportedMediaType("text/plain"), 415, ErrorCode.UNSUPPORTED_MEDIA_TYPE),
        (exceptions.NotAuthenticated(), 401, ErrorCode.NOT_AUTHENTICATED),
        (exceptions.PermissionDenied(), 403, ErrorCode.PERMISSION_DENIED),
    ],
)
def test_drf_exceptions_map_to_codes(exc: Exception, status_code: int, code: ErrorCode) -> None:
    actual_status, error = handle(exc)

    assert actual_status == status_code
    assert error["code"] == code
    assert error["message"]
    assert error["fields"] == {}


def test_throttled_keeps_retry_after_header() -> None:
    response = api_exception_handler(exceptions.Throttled(wait=30), {})

    assert response.status_code == 429
    assert response.data["error"]["code"] == "throttled"
    assert response["Retry-After"] == "30"


def test_unexpected_errors_never_leak_details() -> None:
    status_code, error = handle(RuntimeError("database password is hunter2"))

    assert status_code == 500
    assert error == {"code": "internal_error", "message": INTERNAL_MESSAGE, "fields": {}}


def test_unknown_api_url_returns_the_envelope(client: Client) -> None:
    response = client.get("/api/v1/does-not-exist/")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Not found.", "fields": {}}
    }


def test_non_api_url_keeps_the_html_404(client: Client) -> None:
    response = client.get("/does-not-exist/")

    assert response.status_code == 404
    assert response["Content-Type"].startswith("text/html")


class _Gone(exceptions.APIException):
    status_code = 410
    default_detail = "This resource is gone."


class _Unavailable(exceptions.APIException):
    status_code = 503
    default_detail = "Down for maintenance."


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (_Gone(), ErrorCode.BAD_REQUEST),
        (_Unavailable(), ErrorCode.INTERNAL_ERROR),
        (exceptions.APIException(code="x"), ErrorCode.INTERNAL_ERROR),
    ],
)
def test_unmapped_api_exceptions_are_classified_by_status(exc: Exception, code: ErrorCode) -> None:
    _, error = handle(exc)

    assert error["code"] == code
    assert error["message"]


def test_structured_detail_keeps_its_message() -> None:
    _, error = handle(exceptions.PermissionDenied({"reason": "Account locked"}))

    assert error["message"] == "Account locked"


def test_unexpected_errors_roll_back_the_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[None] = []
    monkeypatch.setattr(handler, "set_rollback", lambda: calls.append(None))

    handle(RuntimeError("boom"))

    assert calls == [None]
