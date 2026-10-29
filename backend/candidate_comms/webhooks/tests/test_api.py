from typing import Any

import pytest
from django.conf import settings
from django.test import Client

from candidate_comms.communications.models import Message, MessageEvent, MessageStatus
from candidate_comms.communications.tests.factories import MessageFactory
from candidate_comms.integrations.messaging.tests.signing import signed_webhook

pytestmark = pytest.mark.django_db

URL = "/api/v1/webhooks/simulator/"


def _event(message: Message, status: str, event_id: str, **extra: Any) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "message_id": message.provider_message_id or "unknown",
        "idempotency_key": str(message.idempotency_key),
        "status": status,
        "occurred_at": "2026-10-29T10:00:00Z",
        "error": None,
        **extra,
    }


def _post(client: Client, payload: dict[str, Any], secret: str | None = None) -> Any:
    body, headers = signed_webhook(payload, secret=secret or settings.SIMULATOR_WEBHOOK_SECRET)
    return client.post(URL, data=body, content_type="application/json", headers=headers)


def test_webhook_applies_a_delivery_update(client: Client) -> None:
    message = MessageFactory.create(status=MessageStatus.SENT, provider_message_id="msg_1")

    response = _post(client, _event(message, "delivered", "evt_1"))

    message.refresh_from_db()
    assert response.status_code == 200
    assert response.json() == {"received": 1, "applied": 1, "ignored": 0}
    assert message.status == MessageStatus.DELIVERED


def test_redelivered_webhook_is_acknowledged_without_changes(client: Client) -> None:
    message = MessageFactory.create(status=MessageStatus.SENT, provider_message_id="msg_1")
    payload = _event(message, "delivered", "evt_1")

    _post(client, payload)
    response = _post(client, payload)

    assert response.status_code == 200
    assert response.json()["ignored"] == 1
    assert MessageEvent.objects.filter(message=message).count() == 1


def test_out_of_order_webhooks_keep_the_latest_status(client: Client) -> None:
    message = MessageFactory.create(status=MessageStatus.SENT, provider_message_id="msg_1")

    _post(client, _event(message, "read", "evt_2"))
    _post(client, _event(message, "delivered", "evt_1"))

    message.refresh_from_db()
    assert message.status == MessageStatus.READ
    assert message.delivered_at is not None


def test_webhook_before_send_result_matches_by_idempotency_key(client: Client) -> None:
    message = MessageFactory.create(status=MessageStatus.QUEUED)
    payload = {**_event(message, "sent", "evt_1"), "message_id": "msg_9"}

    _post(client, payload)

    message.refresh_from_db()
    assert message.status == MessageStatus.SENT
    assert message.provider_message_id == "msg_9"


def test_failed_webhook_stores_the_reason(client: Client) -> None:
    message = MessageFactory.create(status=MessageStatus.SENT, provider_message_id="msg_1")
    error = {"code": "delivery_failed", "message": "Handset unreachable"}

    _post(client, _event(message, "failed", "evt_1", error=error))

    message.refresh_from_db()
    assert message.status == MessageStatus.FAILED
    assert message.failure_code == "delivery_failed"
    assert message.is_retryable is True


def test_unmatched_webhook_is_acknowledged(client: Client) -> None:
    payload = {
        "event_id": "evt_1",
        "message_id": "msg_404",
        "status": "delivered",
        "occurred_at": "2026-10-29T10:00:00Z",
    }

    response = _post(client, payload)

    assert response.status_code == 200
    assert response.json() == {"received": 1, "applied": 0, "ignored": 1}


def test_invalid_signature_is_rejected(client: Client) -> None:
    message = MessageFactory.create(status=MessageStatus.SENT, provider_message_id="msg_1")

    response = _post(client, _event(message, "delivered", "evt_1"), secret="wrong-secret")

    message.refresh_from_db()
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_webhook_signature"
    assert message.status == MessageStatus.SENT


def test_unknown_gateway_is_not_found(client: Client) -> None:
    response = client.post("/api/v1/webhooks/nope/", data=b"{}", content_type="application/json")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
