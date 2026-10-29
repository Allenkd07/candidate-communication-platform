"""Applying gateway status events, and repairing messages whose signals were lost."""

import logging
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from candidate_comms.integrations.messaging.base import StatusEvent
from candidate_comms.integrations.messaging.exceptions import GatewayError
from candidate_comms.integrations.messaging.registry import get_gateway

from ..models import EventSource, Message, MessageStatus
from ..state_machine import Transition
from .delivery import ApplyResult, Failure, message_apply_status
from .dispatch import message_enqueue_send, message_fail

logger = logging.getLogger(__name__)


def _find_message(*, gateway: str, event: StatusEvent) -> Message | None:
    lookup = Q(gateway=gateway, provider_message_id=event.provider_message_id)
    if event.idempotency_key:
        # The webhook can arrive before the send task has stored provider_message_id.
        lookup |= Q(gateway=gateway, idempotency_key=event.idempotency_key)
    return Message.objects.filter(lookup).first()


def status_event_apply(
    *, gateway: str, event: StatusEvent, source: EventSource
) -> ApplyResult | None:
    """Apply one normalized gateway event. Returns None when no message matches it."""
    message = _find_message(gateway=gateway, event=event)
    if message is None:
        logger.warning(
            "No message for %s event %s (provider id %s)",
            gateway,
            event.provider_event_id,
            event.provider_message_id,
        )
        return None
    if not message.provider_message_id:
        Message.objects.filter(id=message.id, provider_message_id="").update(
            provider_message_id=event.provider_message_id
        )
    return message_apply_status(
        message_id=message.id,
        status=MessageStatus(event.status.value),
        source=source,
        occurred_at=event.occurred_at,
        failure=Failure.from_gateway_error(event.error) if event.error else None,
        gateway=gateway,
        provider_event_id=event.provider_event_id,
        payload=dict(event.raw or {}),
    )


@dataclass(frozen=True)
class ReconcileResult:
    checked: int
    updated: int
    requeued: int
    abandoned: int


# Used when a message used up its attempts without a gateway error (e.g. the task crashed).
ATTEMPTS_EXHAUSTED = Failure(
    code="send_attempts_exhausted",
    reason="Sending kept failing, so automatic retries stopped. Retry the message.",
    is_retryable=True,
)


def stale_messages_reconcile() -> ReconcileResult:
    """Poll the gateway for messages stuck in SENT and re-enqueue messages stuck in QUEUED.

    SENT covers lost webhooks; QUEUED covers send tasks lost before they ran. Re-enqueueing
    is safe because a send only proceeds while the message is still QUEUED. A QUEUED message
    that already used every attempt is failed instead, so a task that keeps crashing cannot
    be re-enqueued forever.
    """
    now = timezone.now()
    limit: int = settings.RECONCILE_BATCH_SIZE

    stale_sent: list[tuple[UUID, str, str]] = list(
        Message.objects.filter(
            status=MessageStatus.SENT,
            status_changed_at__lt=now - timedelta(seconds=settings.RECONCILE_SENT_AFTER_SECONDS),
        )
        .exclude(provider_message_id="")
        .order_by("status_changed_at")
        .values_list("id", "gateway", "provider_message_id")[:limit]
    )
    updated = 0
    for message_id, gateway_name, provider_message_id in stale_sent:
        if _reconcile_sent(message_id, gateway_name, provider_message_id):
            updated += 1

    stale_queued: list[tuple[UUID, int]] = list(
        Message.objects.filter(
            status=MessageStatus.QUEUED,
            status_changed_at__lt=now - timedelta(seconds=settings.RECONCILE_QUEUED_AFTER_SECONDS),
        )
        .order_by("status_changed_at")
        .values_list("id", "attempt_count")[:limit]
    )
    max_attempts: int = settings.MESSAGE_SEND_MAX_RETRIES + 1
    requeued = abandoned = 0
    for message_id, attempt_count in stale_queued:
        if attempt_count >= max_attempts:
            message_fail(message_id=message_id, failure=ATTEMPTS_EXHAUSTED)
            abandoned += 1
            continue
        # Restarts the staleness clock so the next run does not enqueue it again.
        Message.objects.filter(id=message_id, status=MessageStatus.QUEUED).update(
            status_changed_at=now
        )
        transaction.on_commit(partial(message_enqueue_send, message_id))
        requeued += 1

    return ReconcileResult(
        checked=len(stale_sent), updated=updated, requeued=requeued, abandoned=abandoned
    )


def _reconcile_sent(message_id: UUID, gateway_name: str, provider_message_id: str) -> bool:
    gateway = get_gateway(gateway_name)
    try:
        event = gateway.fetch_status(provider_message_id)
    except GatewayError as error:
        logger.warning("Reconciliation of message %s failed: %r", message_id, error)
        return False
    if event is None:
        return False
    result = status_event_apply(
        gateway=gateway_name, event=event, source=EventSource.RECONCILIATION
    )
    return result is not None and result.transition == Transition.APPLY
