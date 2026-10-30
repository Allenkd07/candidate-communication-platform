import base64
import hashlib
import hmac
import json
import time

import pytest
import responses

from candidate_comms.integrations.messaging.base import DeliveryStatus, HealthStatus, SendRequest
from candidate_comms.integrations.messaging.exceptions import (
    GatewayUnavailableError,
    InvalidRecipientError,
    RateLimitedError,
    WebhookVerificationError,
)
from candidate_comms.integrations.messaging.resend.gateway import (
    EmailBouncedError,
    EmailRejectedError,
    InvalidEmailError,
    ResendGateway,
)

BASE_URL = "https://resend.test"
SECRET = "whsec_" + base64.b64encode(b"test-secret").decode()
REQUEST = SendRequest(
    recipient="taylor@example.com",
    body="Hello",
    idempotency_key="key-1",
    callback_url="https://unused",
)


@pytest.fixture
def gateway() -> ResendGateway:
    return ResendGateway(
        base_url=BASE_URL,
        api_key="re_test",
        sender="Recruiting <hiring@example.com>",
        subject="Update on your application",
        webhook_secret=SECRET,
        timeout=1,
    )


def signed(payload: dict[str, object], *, secret: str = SECRET) -> tuple[dict[str, str], bytes]:
    body = json.dumps(payload).encode()
    message_id, timestamp = "msg_1", str(int(time.time()))
    key = base64.b64decode(secret.removeprefix("whsec_"))
    digest = hmac.new(key, f"{message_id}.{timestamp}.".encode() + body, hashlib.sha256).digest()
    headers = {
        "svix-id": message_id,
        "svix-timestamp": timestamp,
        "svix-signature": f"v1,{base64.b64encode(digest).decode()}",
    }
    return headers, body


@responses.activate
def test_send_posts_the_email_with_the_idempotency_key(gateway: ResendGateway) -> None:
    responses.post(f"{BASE_URL}/emails", json={"id": "em_1"})

    result = gateway.send(REQUEST)

    call = responses.calls[0].request
    assert result.provider_message_id == "em_1"
    assert call.headers["Idempotency-Key"] == "key-1"
    assert call.headers["Authorization"] == "Bearer re_test"
    assert json.loads(call.body or b"") == {
        "from": "Recruiting <hiring@example.com>",
        "to": ["taylor@example.com"],
        "subject": "Update on your application",
        "text": "Hello",
    }


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (422, InvalidEmailError),
        (403, EmailRejectedError),
        (429, RateLimitedError),
        (503, GatewayUnavailableError),
    ],
)
@responses.activate
def test_errors_are_normalized(gateway: ResendGateway, status: int, error: type[Exception]) -> None:
    responses.post(f"{BASE_URL}/emails", status=status, json={"message": "nope"})

    with pytest.raises(error):
        gateway.send(REQUEST)


def test_an_invalid_address_reads_as_an_email_problem() -> None:
    assert issubclass(InvalidEmailError, InvalidRecipientError)
    assert "email address" in InvalidEmailError.user_message


@pytest.mark.parametrize(
    ("event_type", "status"),
    [
        ("email.sent", DeliveryStatus.SENT),
        ("email.delivered", DeliveryStatus.DELIVERED),
        ("email.opened", DeliveryStatus.READ),
        ("email.bounced", DeliveryStatus.FAILED),
    ],
)
def test_webhook_events_map_to_statuses(
    gateway: ResendGateway, event_type: str, status: DeliveryStatus
) -> None:
    headers, body = signed(
        {"type": event_type, "created_at": "2026-10-30T10:00:00Z", "data": {"email_id": "em_1"}}
    )

    [event] = gateway.parse_webhook(headers, body)

    assert (event.provider_message_id, event.status, event.provider_event_id) == (
        "em_1",
        status,
        "msg_1",
    )
    assert isinstance(event.error, EmailBouncedError) == (status == DeliveryStatus.FAILED)


def test_untracked_events_change_nothing(gateway: ResendGateway) -> None:
    headers, body = signed(
        {
            "type": "email.clicked",
            "created_at": "2026-10-30T10:00:00Z",
            "data": {"email_id": "em_1"},
        }
    )

    assert gateway.parse_webhook(headers, body) == []


def test_a_bad_signature_is_rejected(gateway: ResendGateway) -> None:
    other = "whsec_" + base64.b64encode(b"other").decode()
    headers, body = signed({"type": "email.sent"}, secret=other)

    with pytest.raises(WebhookVerificationError):
        gateway.parse_webhook(headers, body)


@responses.activate
def test_fetch_status_reads_the_last_event(gateway: ResendGateway) -> None:
    responses.get(f"{BASE_URL}/emails/em_1", json={"id": "em_1", "last_event": "delivered"})
    responses.get(f"{BASE_URL}/emails/em_2", json={"id": "em_2", "last_event": "queued"})

    delivered = gateway.fetch_status("em_1")

    assert delivered is not None and delivered.status == DeliveryStatus.DELIVERED
    assert gateway.fetch_status("em_2") is None


@responses.activate
def test_health(gateway: ResendGateway) -> None:
    restricted = {"message": "This API key is restricted to only send emails"}
    responses.get(f"{BASE_URL}/domains", status=401, json=restricted)
    assert gateway.health().status == HealthStatus.OPERATIONAL

    responses.replace(responses.GET, f"{BASE_URL}/domains", status=401, json={"message": "Invalid"})
    assert gateway.health().status == HealthStatus.DOWN

    responses.replace(responses.GET, f"{BASE_URL}/domains", status=503)
    assert gateway.health().status == HealthStatus.DOWN
