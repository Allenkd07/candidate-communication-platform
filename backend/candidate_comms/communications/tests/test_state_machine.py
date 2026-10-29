import itertools

import pytest

from candidate_comms.communications.models import MessageStatus as S
from candidate_comms.communications.state_machine import Transition as T  # noqa: N817
from candidate_comms.communications.state_machine import evaluate

# Expected outcome for every (current, new) pair; rows are the current status.
EXPECTED: dict[S, dict[S, T]] = {
    S.SCHEDULED: {
        S.SCHEDULED: T.DUPLICATE,
        S.QUEUED: T.APPLY,
        S.SENT: T.APPLY,
        S.DELIVERED: T.APPLY,
        S.READ: T.APPLY,
        S.FAILED: T.STALE,
    },
    S.QUEUED: {
        S.SCHEDULED: T.STALE,
        S.QUEUED: T.DUPLICATE,
        S.SENT: T.APPLY,
        S.DELIVERED: T.APPLY,
        S.READ: T.APPLY,
        S.FAILED: T.APPLY,
    },
    S.SENT: {
        S.SCHEDULED: T.STALE,
        S.QUEUED: T.STALE,
        S.SENT: T.DUPLICATE,
        S.DELIVERED: T.APPLY,
        S.READ: T.APPLY,
        S.FAILED: T.APPLY,
    },
    S.DELIVERED: {
        S.SCHEDULED: T.STALE,
        S.QUEUED: T.STALE,
        S.SENT: T.STALE,
        S.DELIVERED: T.DUPLICATE,
        S.READ: T.APPLY,
        S.FAILED: T.STALE,
    },
    S.READ: {
        S.SCHEDULED: T.STALE,
        S.QUEUED: T.STALE,
        S.SENT: T.STALE,
        S.DELIVERED: T.STALE,
        S.READ: T.DUPLICATE,
        S.FAILED: T.STALE,
    },
    S.FAILED: {
        S.SCHEDULED: T.REJECTED,
        S.QUEUED: T.REJECTED,
        S.SENT: T.REJECTED,
        S.DELIVERED: T.REJECTED,
        S.READ: T.REJECTED,
        S.FAILED: T.DUPLICATE,
    },
}


def test_expectations_cover_every_pair() -> None:
    pairs = {(current, new) for current, row in EXPECTED.items() for new in row}
    assert pairs == set(itertools.product(S, S))


@pytest.mark.parametrize(
    ("current", "new"), [(current, new) for current in EXPECTED for new in EXPECTED[current]]
)
def test_transition(current: S, new: S) -> None:
    assert evaluate(current, new) == EXPECTED[current][new]
