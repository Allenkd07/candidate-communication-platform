"""Forward-only delivery status transitions.

SCHEDULED → QUEUED → SENT → DELIVERED → READ, and QUEUED or SENT → FAILED.
Skipping ahead is allowed (a READ signal implies the message was delivered), so a lost
webhook never blocks later ones. FAILED is terminal for provider signals.
"""

from enum import StrEnum

from .models import MessageStatus

_PROGRESSION: tuple[MessageStatus, ...] = (
    MessageStatus.SCHEDULED,
    MessageStatus.QUEUED,
    MessageStatus.SENT,
    MessageStatus.DELIVERED,
    MessageStatus.READ,
)
_RANK = {status: rank for rank, status in enumerate(_PROGRESSION)}
_CAN_FAIL_FROM = frozenset({MessageStatus.QUEUED, MessageStatus.SENT})


class Transition(StrEnum):
    APPLY = "apply"
    DUPLICATE = "duplicate"  # Same status again: a re-delivered or repeated signal.
    STALE = "stale"  # Older than the current status: arrived out of order.
    REJECTED = "rejected"  # Not reachable from the current status (e.g. after FAILED).


def evaluate(current: MessageStatus, new: MessageStatus) -> Transition:
    if new == current:
        return Transition.DUPLICATE
    if current == MessageStatus.FAILED:
        return Transition.REJECTED
    if new == MessageStatus.FAILED:
        return Transition.APPLY if current in _CAN_FAIL_FROM else Transition.STALE
    if new == MessageStatus.SCHEDULED:
        return Transition.STALE
    return Transition.APPLY if _RANK[new] > _RANK[current] else Transition.STALE
