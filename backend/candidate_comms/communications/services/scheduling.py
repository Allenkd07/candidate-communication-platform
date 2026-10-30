"""Releasing scheduled messages when their time comes."""

from dataclasses import dataclass

from django.utils import timezone

from ..models import EventSource, Message, MessageStatus
from ..state_machine import Transition
from .delivery import Failure, message_apply_status
from .dispatch import message_enqueue_send, message_fail

RELEASE_BATCH_SIZE = 200

CANDIDATE_DELETED = Failure(
    code="candidate_deleted",
    reason="Not sent: the candidate was deleted before the scheduled time.",
    is_retryable=False,
)


@dataclass(frozen=True)
class ReleaseResult:
    released: int
    cancelled: int


def scheduled_messages_release() -> ReleaseResult:
    """Queue every scheduled message that is due and hand it to a worker.

    Each move goes through the state machine under a row lock, so a message released twice
    (overlapping runs) is queued once. A deleted candidate's message fails instead of sending.
    """
    due = (
        Message.objects.filter(status=MessageStatus.SCHEDULED, scheduled_for__lte=timezone.now())
        .order_by("scheduled_for")
        .values_list("id", "candidate__is_deleted")[:RELEASE_BATCH_SIZE]
    )
    released = cancelled = 0
    for message_id, candidate_deleted in due:
        result = message_apply_status(
            message_id=message_id, status=MessageStatus.QUEUED, source=EventSource.PLATFORM
        )
        if result.transition != Transition.APPLY:
            continue
        if candidate_deleted:
            message_fail(message_id=message_id, failure=CANDIDATE_DELETED)
            cancelled += 1
        else:
            message_enqueue_send(message_id)
            released += 1
    return ReleaseResult(released=released, cancelled=cancelled)
