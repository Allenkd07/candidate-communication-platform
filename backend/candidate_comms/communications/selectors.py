from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from candidate_comms.candidates.selectors import candidate_get

from .models import Message, MessageBatch, MessageStatus


def candidate_message_history(*, candidate_id: UUID) -> QuerySet[Message]:
    """A candidate's messages, newest first. Raises Http404 for an unknown candidate."""
    candidate = candidate_get(candidate_id=candidate_id)
    return Message.objects.filter(candidate=candidate).order_by("-created_at")


@dataclass(frozen=True)
class BatchSummary:
    batch: MessageBatch
    messages: list[Message]
    counts: dict[str, int]

    @property
    def total(self) -> int:
        return len(self.messages)


def batch_summary(*, batch_id: UUID) -> BatchSummary:
    """A batch with every recipient's current status and a per-status count."""
    batch = get_object_or_404(MessageBatch, id=batch_id)
    messages = list(
        batch.messages.select_related("candidate").order_by("candidate__full_name", "id")
    )
    tally = Counter(message.status for message in messages)
    counts = {status.value: tally.get(status.value, 0) for status in MessageStatus}
    return BatchSummary(batch=batch, messages=messages, counts=counts)
