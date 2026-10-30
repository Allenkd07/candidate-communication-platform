import json
import time
from datetime import UTC, datetime

import pytest
import requests
import responses
from django.conf import settings

from candidate_comms.integrations.messaging.base import DeliveryStatus, HealthStatus, SendRequest
from candidate_comms.integrations.messaging.exceptions import (
    DeliveryFailedError,
    GatewayError,
    GatewayRejectedError,
    GatewayUnavailableError,
    InvalidRecipientError,
    RateLimitedError,
    WebhookPayloadError,
    WebhookVerificationError,
)
from candidate_comms.integrations.messaging.simulator.gateway import SimulatorGateway

from .signing import signed_webhook

BASE_URL = settings.SIMULATOR_API_URL.rstrip("/")
SECRET = settings.SIMULATOR_WEBHOOK_SECRET
REQUEST = SendRequest(
    recipient="+919845012345",
    body="Hello",
    idempotency_key="key-1",
    callback_url=f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/simulator/",
)
EVENT = {
    "event_id": "evt_1",
    "message_id": "msg_1",
    "idempotency_key": "key-1",
    "status": "delivered",
    "occurred_at": "2026-10-29T10:00:00Z",
    "error": None,
}


@pytest.fixture
def gateway() -> SimulatorGateway:
    return SimulatorGateway(
        base_url=BASE_URL, api_key=settings.SIMULATOR_API_KEY, webhook_secret=SECRET, timeout=1
    )


@responses.activate
def test_send_posts_the_message_with_auth_and_idempotency_key(gateway: SimulatorGateway) -> None:
    responses.post(
        f"{BASE_URL}/v1/messages", status=202, json={"id": "msg_1", "status": "accepted"}
    )

    result = gateway.send(REQUEST)

    assert result.provider_message_id == "msg_1"
    [call] = responses.calls
    assert call.request.headers["Authorization"] == f"Bearer {settings.SIMULATOR_API_KEY}"
    assert json.loads(call.request.body or b"") == {
        "to": "+919845012345",
        "body": "Hello",
        "idempotency_key": "key-1",
        "callback_url": REQUEST.callback_url,
    }


@pytest.mark.parametrize(
    ("status", "body", "error_class"),
    [
        (422, {"error": {"code": "invalid_recipient", "message": "bad"}}, InvalidRecipientError),
        (400, {"error": {"code": "invalid_recipient", "message": "bad"}}, InvalidRecipientError),
        (503, {"error": {"code": "unavailable", "message": "down"}}, GatewayUnavailableError),
        (500, None, GatewayUnavailableError),
        (401, {"error": {"code": "unauthorized", "message": "no"}}, GatewayRejectedError),
        (400, {"error": {"code": "content_rejected", "message": "no"}}, GatewayRejectedError),
        (409, {"error": {"code": "idempotency_key_reused", "message": "no"}}, GatewayRejectedError),
    ],
)
@responses.activate
def test_send_maps_http_errors(
    gateway: SimulatorGateway, status: int, body: object, error_class: type[GatewayError]
) -> None:
    responses.post(f"{BASE_URL}/v1/messages", status=status, json=body)

    with pytest.raises(error_class):
        gateway.send(REQUEST)


@responses.activate
def test_rate_limit_carries_retry_after(gateway: SimulatorGateway) -> None:
    responses.post(f"{BASE_URL}/v1/messages", status=429, headers={"Retry-After": "7"}, json={})

    with pytest.raises(RateLimitedError) as exc_info:
        gateway.send(REQUEST)

    assert exc_info.value.retry_after == 7
    assert exc_info.value.retryable is True


@responses.activate
def test_connection_errors_mean_unavailable(gateway: SimulatorGateway) -> None:
    responses.post(f"{BASE_URL}/v1/messages", body=requests.ConnectionError("refused"))

    with pytest.raises(GatewayUnavailableError):
        gateway.send(REQUEST)


def test_parse_webhook_accepts_a_valid_signature(gateway: SimulatorGateway) -> None:
    body, headers = signed_webhook(EVENT, secret=SECRET)

    [event] = gateway.parse_webhook(headers, body)

    assert event.provider_event_id == "evt_1"
    assert event.provider_message_id == "msg_1"
    assert event.idempotency_key == "key-1"
    assert event.status == DeliveryStatus.DELIVERED
    assert event.occurred_at == datetime(2026, 10, 29, 10, tzinfo=UTC)
    assert event.error is None


def test_failed_webhook_maps_the_error_code(gateway: SimulatorGateway) -> None:
    payload = {**EVENT, "status": "failed", "error": {"code": "delivery_failed", "message": "x"}}
    body, headers = signed_webhook(payload, secret=SECRET)

    [event] = gateway.parse_webhook(headers, body)

    assert isinstance(event.error, DeliveryFailedError)


@pytest.mark.parametrize(
    "tamper",
    [
        lambda body, headers: (body + b" ", headers),
        lambda body, headers: (body, {}),
        lambda body, headers: (body, {"X-Simulator-Signature": "t=abc,v1=00"}),
    ],
    ids=["modified-body", "missing-header", "malformed-header"],
)
def test_parse_webhook_rejects_bad_signatures(gateway: SimulatorGateway, tamper: object) -> None:
    body, headers = tamper(*signed_webhook(EVENT, secret=SECRET))  # type: ignore[operator]

    with pytest.raises(WebhookVerificationError):
        gateway.parse_webhook(headers, body)


def test_parse_webhook_rejects_old_signatures(gateway: SimulatorGateway) -> None:
    body, headers = signed_webhook(EVENT, secret=SECRET, timestamp=int(time.time()) - 301)

    with pytest.raises(WebhookVerificationError):
        gateway.parse_webhook(headers, body)


def test_parse_webhook_rejects_unknown_statuses(gateway: SimulatorGateway) -> None:
    body, headers = signed_webhook({**EVENT, "status": "teleported"}, secret=SECRET)

    with pytest.raises(WebhookPayloadError):
        gateway.parse_webhook(headers, body)


@responses.activate
def test_fetch_status_returns_none_until_reportable(gateway: SimulatorGateway) -> None:
    responses.get(
        f"{BASE_URL}/v1/messages/msg_1",
        json={"id": "msg_1", "status": "accepted", "updated_at": "2026-10-29T10:00:00Z"},
    )

    assert gateway.fetch_status("msg_1") is None


@responses.activate
def test_fetch_status_returns_the_current_status(gateway: SimulatorGateway) -> None:
    responses.get(
        f"{BASE_URL}/v1/messages/msg_1",
        json={"id": "msg_1", "status": "read", "updated_at": "2026-10-29T10:00:00+00:00"},
    )

    event = gateway.fetch_status("msg_1")

    assert event is not None
    assert (event.status, event.provider_event_id) == (DeliveryStatus.READ, None)


@responses.activate
def test_health_reports_down_when_unreachable(gateway: SimulatorGateway) -> None:
    responses.get(f"{BASE_URL}/health", body=requests.ConnectionError("refused"))

    assert gateway.health().status == HealthStatus.DOWN


@responses.activate
def test_success_body_that_is_not_an_object_is_rejected(gateway: SimulatorGateway) -> None:
    responses.post(f"{BASE_URL}/v1/messages", status=202, json=["msg_1"])

    with pytest.raises(GatewayRejectedError):
        gateway.send(REQUEST)


@pytest.mark.parametrize("body", [["oops"], "oops", {"error": "rate limited"}])
@responses.activate
def test_error_body_that_is_not_an_object_still_maps(
    gateway: SimulatorGateway, body: object
) -> None:
    responses.post(f"{BASE_URL}/v1/messages", status=503, json=body)

    with pytest.raises(GatewayUnavailableError):
        gateway.send(REQUEST)


def test_failed_webhook_with_a_non_object_error_uses_the_fallback(
    gateway: SimulatorGateway,
) -> None:
    body, headers = signed_webhook({**EVENT, "status": "failed", "error": "boom"}, secret=SECRET)

    [event] = gateway.parse_webhook(headers, body)

    assert isinstance(event.error, GatewayRejectedError)
