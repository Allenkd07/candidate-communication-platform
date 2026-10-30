"""Creating message batches and handing each message to its gateway."""

import logging
import random
from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from candidate_comms.candidates.models import Candidate
from candidate_comms.core.exceptions import ApplicationError, ErrorCode
from candidate_comms.integrations.messaging.base import SendRequest
from candidate_comms.integrations.messaging.exceptions import GatewayError
from candidate_comms.integrations.messaging.registry import default_gateway_name, get_gateway

from ..models import (
    MESSAGE_BODY_MAX_LENGTH,
    Channel,
    EventSource,
    Message,
    MessageBatch,
    MessageEvent,
    MessageStatus,
)
from .delivery import Failure, message_apply_status

logger = logging.getLogger(__name__)

MAX_RECIPIENTS = 500


def message_enqueue_send(message_id: UUID) -> None:
    from ..tasks import send_message

    send_message.delay(str(message_id))


def _validate_send(*, candidate_ids: Sequence[UUID], body: str) -> tuple[list[UUID], str]:
    body = body.strip()
    if not body:
        raise ApplicationError("Message can't be empty.", fields={"body": ["Enter a message."]})
    if len(body) > MESSAGE_BODY_MAX_LENGTH:
        limit = f"Use at most {MESSAGE_BODY_MAX_LENGTH} characters."
        raise ApplicationError("Message is too long.", fields={"body": [limit]})
    unique_ids = list(dict.fromkeys(candidate_ids))
    if not 1 <= len(unique_ids) <= MAX_RECIPIENTS:
        limit = f"Choose between 1 and {MAX_RECIPIENTS} recipients."
        raise ApplicationError(limit, fields={"candidate_ids": [limit]})
    return unique_ids, body


def batch_create(*, candidate_ids: Sequence[UUID], body: str, channel: Channel) -> MessageBatch:
    """Create a batch with one QUEUED message per candidate, then enqueue one task each.

    Tasks are enqueued after commit, so a worker never picks up an unsaved message, and one
    failing recipient never blocks the others.
    """
    unique_ids, body = _validate_send(candidate_ids=candidate_ids, body=body)
    gateway = default_gateway_name(channel)
    now = timezone.now()

    with transaction.atomic():
        candidates = Candidate.objects.in_bulk(unique_ids)
        missing = [
            str(candidate_id) for candidate_id in unique_ids if candidate_id not in candidates
        ]
        if missing:
            raise ApplicationError(
                "Some recipients no longer exist. Refresh the list and try again.",
                code=ErrorCode.NOT_FOUND,
                status_code=404,
                fields={"candidate_ids": missing},
            )

        batch = MessageBatch.objects.create(body=body, channel=channel, gateway=gateway)
        messages = Message.objects.bulk_create(
            Message(
                batch=batch,
                candidate=candidates[candidate_id],
                channel=channel,
                gateway=gateway,
                recipient=candidates[candidate_id].phone,
                body=body,
                status=MessageStatus.QUEUED,
                status_changed_at=now,
            )
            for candidate_id in unique_ids
        )
        MessageEvent.objects.bulk_create(
            MessageEvent(
                message=message,
                source=EventSource.PLATFORM,
                status=MessageStatus.QUEUED,
                applied=True,
                occurred_at=now,
            )
            for message in messages
        )
        for message in messages:
            transaction.on_commit(partial(message_enqueue_send, message.id))
    return batch


@dataclass(frozen=True)
class AttemptResult:
    sent: bool
    # Set when the attempt failed with an error that is retried automatically.
    retry_error: GatewayError | None = None


def message_send_attempt(*, message_id: UUID) -> AttemptResult:
    """Submit a QUEUED message to its gateway once.

    Only QUEUED messages are submitted, so a re-delivered task is a no-op. Every attempt
    reuses the message's idempotency key, so the gateway never delivers it twice.
    """
    claimed = Message.objects.filter(id=message_id, status=MessageStatus.QUEUED).update(
        attempt_count=F("attempt_count") + 1
    )
    if not claimed:
        logger.info("Message %s is no longer queued; skipping send", message_id)
        return AttemptResult(sent=False)

    message = Message.objects.get(id=message_id)
    gateway = get_gateway(message.gateway)
    request = SendRequest(
        recipient=message.recipient,
        body=message.body,
        idempotency_key=str(message.idempotency_key),
        callback_url=f"{settings.WEBHOOK_BASE_URL.rstrip('/')}/api/v1/webhooks/{gateway.name}/",
    )
    try:
        result = gateway.send(request)
    except GatewayError as error:
        logger.warning(
            "Send attempt %s for message %s failed: %r", message.attempt_count, message_id, error
        )
        if error.retryable:
            return AttemptResult(sent=False, retry_error=error)
        message_fail(message_id=message_id, failure=Failure.from_gateway_error(error))
        return AttemptResult(sent=False)

    Message.objects.filter(id=message_id).update(provider_message_id=result.provider_message_id)
    message_apply_status(
        message_id=message_id,
        status=MessageStatus.SENT,
        source=EventSource.PLATFORM,
        gateway=gateway.name,
        payload={"provider_message_id": result.provider_message_id},
    )
    return AttemptResult(sent=True)


def message_fail(*, message_id: UUID, failure: Failure) -> None:
    message_apply_status(
        message_id=message_id,
        status=MessageStatus.FAILED,
        source=EventSource.PLATFORM,
        failure=failure,
        payload={"failure_code": failure.code},
    )


def retry_delay_seconds(*, retries: int, error: GatewayError) -> float:
    """Delay before the next automatic retry, given `retries` retries so far.

    Honours the gateway's Retry-After; otherwise exponential backoff with jitter, never
    less than half the base delay so a retry is never immediate.
    """
    max_delay: float = settings.MESSAGE_RETRY_MAX_DELAY_SECONDS
    if error.retry_after is not None:
        return min(error.retry_after, max_delay)
    base: float = settings.MESSAGE_RETRY_BASE_DELAY_SECONDS
    return random.uniform(base / 2, min(base * 2**retries, max_delay))
