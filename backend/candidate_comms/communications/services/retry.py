"""Manual retries: a failed message is sent again as a new message in the same batch."""

from collections.abc import Sequence
from functools import partial
from uuid import UUID

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from candidate_comms.core.exceptions import ApplicationError, ErrorCode

from ..models import EventSource, Message, MessageBatch, MessageEvent, MessageStatus
from ..selectors import RETRYABLE
from .dispatch import message_enqueue_send, recipient_for


def message_retry(*, message_id: UUID) -> Message:
    """Send one failed message again. Raises 409 not_retryable when the rules don't allow it."""
    with transaction.atomic():
        original = get_object_or_404(
            Message.objects.select_for_update(of=("self",)).select_related("candidate"),
            id=message_id,
        )
        if not Message.objects.filter(RETRYABLE, id=original.id).exists():
            raise _not_retryable("This message can't be retried.")
        [retry] = _create_retries([original])
    return retry


def batch_retry_failed(*, batch_id: UUID) -> list[Message]:
    """Send every retryable failed message of a batch again."""
    with transaction.atomic():
        get_object_or_404(MessageBatch, id=batch_id)
        locked = list(
            Message.objects.select_for_update(of=("self",))
            .filter(RETRYABLE, batch_id=batch_id)
            .values_list("id", flat=True)
        )
        # Re-read under the locks: a concurrent retry may have committed.
        originals = list(
            Message.objects.select_related("candidate").filter(RETRYABLE, id__in=locked)
        )
        if not originals:
            raise _not_retryable("Nothing in this send can be retried.")
        try:
            with transaction.atomic():
                return _create_retries(originals)
        except IntegrityError:
            raise _not_retryable("Nothing in this send can be retried.") from None


def _not_retryable(message: str) -> ApplicationError:
    return ApplicationError(message, code=ErrorCode.NOT_RETRYABLE, status_code=409)


def _create_retries(originals: Sequence[Message]) -> list[Message]:
    """New QUEUED messages with fresh idempotency keys, enqueued after commit.

    The key must be fresh: for the old one the provider would replay the original failure.
    """
    now = timezone.now()
    retries = Message.objects.bulk_create(
        Message(
            batch_id=original.batch_id,
            candidate=original.candidate,
            channel=original.channel,
            gateway=original.gateway,
            recipient=recipient_for(original.candidate, original.channel),
            body=original.body,
            status=MessageStatus.QUEUED,
            status_changed_at=now,
            retry_of=original,
        )
        for original in originals
    )
    MessageEvent.objects.bulk_create(
        MessageEvent(
            message=retry,
            source=EventSource.PLATFORM,
            status=MessageStatus.QUEUED,
            applied=True,
            occurred_at=now,
        )
        for retry in retries
    )
    for retry in retries:
        transaction.on_commit(partial(message_enqueue_send, retry.id))
    return retries
