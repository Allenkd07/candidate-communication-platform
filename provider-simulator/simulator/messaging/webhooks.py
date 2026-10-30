"""Signed webhook delivery to the platform's callback URL.

Signature header: X-Simulator-Signature: t=<unix seconds>,v1=<hex>, where
v1 = HMAC-SHA256(SIMULATOR_WEBHOOK_SECRET, f"{t}.{raw body}"). Each attempt is signed with
a fresh timestamp, so a retry is never rejected as too old.
"""

import hashlib
import hmac
import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings
from django.db.models import F
from django.db.models.functions import Coalesce, Now

from .models import MessageStatus, WebhookEvent

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-Simulator-Signature"


def sign(body: bytes, *, secret: str, timestamp: int) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"t={timestamp},v1={digest.hexdigest()}"


def webhook_payload(event: WebhookEvent) -> dict[str, Any]:
    message = event.message
    error = None
    if event.status == MessageStatus.FAILED:
        error = {"code": message.error_code, "message": message.error_message}
    return {
        "event_id": event.id,
        "message_id": message.id,
        "idempotency_key": message.idempotency_key,
        "status": event.status,
        "occurred_at": event.occurred_at.isoformat(),
        "error": error,
    }


def webhook_schedule(event_id: str) -> None:
    """Queue delivery, sometimes late (to arrive out of order) and sometimes twice."""
    from .tasks import deliver_webhook

    countdown = 0.0
    if random.random() < settings.WEBHOOK_OUT_OF_ORDER_RATE:
        countdown = settings.WEBHOOK_OUT_OF_ORDER_DELAY_SECONDS
    deliver_webhook.apply_async(args=[event_id], countdown=countdown)
    if random.random() < settings.WEBHOOK_DUPLICATE_RATE:
        deliver_webhook.apply_async(args=[event_id], countdown=countdown + 1)


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool
    # Whether another attempt may succeed: network errors, 5xx, 408 and 429.
    retryable: bool = False


def webhook_deliver(*, event_id: str) -> DeliveryResult:
    """POST the event to its callback URL once and record the outcome."""
    event = WebhookEvent.objects.select_related("message").get(id=event_id)
    body = json.dumps(webhook_payload(event)).encode()
    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: sign(
            body, secret=settings.SIMULATOR_WEBHOOK_SECRET, timestamp=int(time.time())
        ),
    }
    WebhookEvent.objects.filter(id=event_id).update(attempts=F("attempts") + 1)

    try:
        response = requests.post(
            event.message.callback_url,
            data=body,
            headers=headers,
            timeout=settings.WEBHOOK_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("Webhook %s failed: %r", event_id, exc)
        WebhookEvent.objects.filter(id=event_id).update(last_error=type(exc).__name__)
        return DeliveryResult(delivered=False, retryable=True)

    if response.ok:
        WebhookEvent.objects.filter(id=event_id).update(
            delivered_at=Coalesce(F("delivered_at"), Now()),
            last_response_status=response.status_code,
            last_error="",
        )
        return DeliveryResult(delivered=True)

    logger.warning("Webhook %s answered HTTP %s", event_id, response.status_code)
    WebhookEvent.objects.filter(id=event_id).update(
        last_response_status=response.status_code, last_error=f"HTTP {response.status_code}"
    )
    retryable = response.status_code >= 500 or response.status_code in (408, 429)
    return DeliveryResult(delivered=False, retryable=retryable)


def webhook_retry_delay_seconds(*, retries: int) -> float:
    return float(min(2**retries, settings.WEBHOOK_RETRY_MAX_DELAY_SECONDS))
