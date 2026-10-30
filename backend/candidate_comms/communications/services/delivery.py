"""Applies status signals (send results, webhooks, reconciliation) through the state machine."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from candidate_comms.integrations.messaging.exceptions import GatewayError
from candidate_comms.realtime.publisher import publish

from ..models import EventSource, Message, MessageEvent, MessageStatus
from ..selectors import RETRYABLE
from ..state_machine import Transition, evaluate

logger = logging.getLogger(__name__)

MESSAGE_STATUS_EVENT = "message.status"

_TIMESTAMP_FIELDS = {
    MessageStatus.SENT: "sent_at",
    MessageStatus.DELIVERED: "delivered_at",
    MessageStatus.READ: "read_at",
    MessageStatus.FAILED: "failed_at",
}
# A status implies every earlier milestone; READ without a DELIVERED webhook is still delivered.
_IMPLIED_MILESTONES = {
    MessageStatus.DELIVERED: (MessageStatus.SENT,),
    MessageStatus.READ: (MessageStatus.SENT, MessageStatus.DELIVERED),
}


@dataclass(frozen=True)
class Failure:
    code: str
    reason: str
    is_retryable: bool

    @classmethod
    def from_gateway_error(
        cls, error: GatewayError, *, retries_exhausted: bool = False
    ) -> "Failure":
        return cls(
            code=error.code,
            reason=error.exhausted_message if retries_exhausted else error.user_message,
            is_retryable=error.manually_retryable,
        )


@dataclass(frozen=True)
class ApplyResult:
    transition: Transition
    message: Message


def message_apply_status(
    *,
    message_id: UUID,
    status: MessageStatus,
    source: EventSource,
    occurred_at: datetime | None = None,
    failure: Failure | None = None,
    gateway: str = "",
    provider_event_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> ApplyResult:
    """Record a status signal and apply it if the state machine allows.

    A provider event id seen before is a duplicate and changes nothing.
    """
    occurred_at = occurred_at or timezone.now()
    with transaction.atomic():
        message = Message.objects.select_for_update().get(id=message_id)
        transition = evaluate(MessageStatus(message.status), status)

        try:
            with transaction.atomic():
                MessageEvent.objects.create(
                    message=message,
                    source=source,
                    status=status,
                    applied=transition == Transition.APPLY,
                    occurred_at=occurred_at,
                    gateway=gateway,
                    provider_event_id=provider_event_id or "",
                    payload=payload or {},
                )
        except IntegrityError:
            logger.info("Duplicate event %s for message %s", provider_event_id, message.id)
            return ApplyResult(Transition.DUPLICATE, message)

        if transition != Transition.APPLY:
            logger.info(
                "Ignored %s signal for message %s: %s (current %s)",
                status,
                message.id,
                transition,
                message.status,
            )
            return ApplyResult(transition, message)

        _set_status(message, status, occurred_at, failure)
        message.save()
        transaction.on_commit(lambda: publish_message_status(message))
    return ApplyResult(transition, message)


def _set_status(
    message: Message, status: MessageStatus, occurred_at: datetime, failure: Failure | None
) -> None:
    message.status = status
    message.status_changed_at = timezone.now()
    for milestone in (*_IMPLIED_MILESTONES.get(status, ()), status):
        field = _TIMESTAMP_FIELDS.get(milestone)
        if field and getattr(message, field) is None:
            setattr(message, field, occurred_at)
    if status == MessageStatus.FAILED:
        failure = failure or Failure(
            code="unknown", reason="The message could not be sent.", is_retryable=False
        )
        message.failure_code = failure.code
        message.failure_reason = failure.reason
        message.is_retryable = failure.is_retryable


def message_status_payload(message: Message) -> dict[str, Any]:
    return {
        "message_id": message.id,
        "batch_id": message.batch_id,
        "candidate_id": message.candidate_id,
        "status": message.status,
        "status_changed_at": message.status_changed_at,
        "failure_code": message.failure_code,
        "failure_reason": message.failure_reason,
        "is_retryable": message.is_retryable,
        "can_retry": Message.objects.filter(RETRYABLE, id=message.id).exists(),
    }


def publish_message_status(message: Message) -> None:
    publish(MESSAGE_STATUS_EVENT, message_status_payload(message))
