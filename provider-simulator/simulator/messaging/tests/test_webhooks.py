import hashlib
import hmac
import json
from datetime import timedelta

import pytest
import requests
import responses
from celery.exceptions import Retry
from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from simulator.messaging import webhooks
from simulator.messaging.models import Message, MessageStatus, WebhookEvent
from simulator.messaging.tasks import deliver_webhook
from simulator.messaging.webhooks import SIGNATURE_HEADER, webhook_deliver, webhook_schedule

pytestmark = pytest.mark.django_db

CALLBACK_URL = "http://api.test/api/v1/webhooks/simulator/"


def _event(status: MessageStatus = MessageStatus.DELIVERED) -> WebhookEvent:
    message = Message.objects.create(
        idempotency_key="key-1",
        to="+919845012345",
        body="Hi",
        callback_url=CALLBACK_URL,
        status=status,
    )
    if status == MessageStatus.FAILED:
        message.error_code, message.error_message = "delivery_failed", "Not delivered."
        message.save()
    return WebhookEvent.objects.create(message=message, status=status, occurred_at=timezone.now())


@responses.activate
def test_webhook_is_signed_over_the_timestamp_and_raw_body() -> None:
    responses.post(CALLBACK_URL, json={"received": 1})
    event = _event()

    result = webhook_deliver(event_id=event.id)

    assert result.delivered is True
    request = responses.calls[0].request
    body = request.body if isinstance(request.body, bytes) else str(request.body).encode()
    parts = dict(part.split("=", 1) for part in request.headers[SIGNATURE_HEADER].split(","))
    expected = hmac.new(
        settings.SIMULATOR_WEBHOOK_SECRET.encode(),
        f"{parts['t']}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()
    assert hmac.compare_digest(parts["v1"], expected)
    assert json.loads(body) == {
        "event_id": event.id,
        "message_id": event.message_id,
        "idempotency_key": "key-1",
        "status": "delivered",
        "occurred_at": event.occurred_at.isoformat(),
        "error": None,
    }
    event.refresh_from_db()
    assert event.delivered_at is not None
    assert event.attempts == 1


@responses.activate
def test_failed_status_carries_the_error() -> None:
    responses.post(CALLBACK_URL)
    event = _event(MessageStatus.FAILED)

    webhook_deliver(event_id=event.id)

    payload = json.loads(responses.calls[0].request.body or b"{}")
    assert payload["error"] == {"code": "delivery_failed", "message": "Not delivered."}


@responses.activate
def test_a_duplicate_delivery_keeps_the_first_delivery_time() -> None:
    responses.post(CALLBACK_URL)
    event = _event()
    # The test runs in one transaction, where NOW() never changes, so the first delivery is
    # dated in the past to tell it apart from the second.
    first_delivered_at = timezone.now() - timedelta(minutes=5)
    WebhookEvent.objects.filter(id=event.id).update(attempts=1, delivered_at=first_delivered_at)

    webhook_deliver(event_id=event.id)

    event.refresh_from_db()
    assert event.attempts == 2
    assert event.delivered_at == first_delivered_at


@responses.activate
@pytest.mark.parametrize(
    ("outcome", "retryable"),
    [(500, True), (429, True), (401, False), (requests.ConnectionError(), True)],
)
def test_undelivered_webhooks_are_retried_only_when_another_attempt_may_succeed(
    outcome: int | Exception, retryable: bool
) -> None:
    if isinstance(outcome, Exception):
        responses.post(CALLBACK_URL, body=outcome)
    else:
        responses.post(CALLBACK_URL, status=outcome)
    event = _event()

    result = webhook_deliver(event_id=event.id)

    assert result.delivered is False
    assert result.retryable is retryable
    event.refresh_from_db()
    assert event.delivered_at is None
    assert event.last_error


@responses.activate
def test_task_retries_then_drops_the_webhook() -> None:
    responses.post(CALLBACK_URL, status=503)
    event = _event()

    with pytest.raises(Retry):
        deliver_webhook.apply(args=[event.id], retries=0)
    deliver_webhook.apply(args=[event.id], retries=deliver_webhook.max_retries)

    event.refresh_from_db()
    assert event.attempts == 2
    assert event.delivered_at is None


@override_settings(
    WEBHOOK_DUPLICATE_RATE=1.0, WEBHOOK_OUT_OF_ORDER_RATE=1.0, WEBHOOK_OUT_OF_ORDER_DELAY_SECONDS=10
)
def test_schedule_can_hold_back_and_duplicate_a_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], float]] = []
    monkeypatch.setattr(
        deliver_webhook,
        "apply_async",
        lambda args, countdown: calls.append((args, countdown)),
    )

    webhook_schedule("EV1")

    assert calls == [(["EV1"], 10), (["EV1"], 11)]


def test_retry_delay_doubles_up_to_the_cap() -> None:
    delays = [webhooks.webhook_retry_delay_seconds(retries=n) for n in (0, 1, 3, 10)]

    assert delays == [1, 2, 8, 60]
