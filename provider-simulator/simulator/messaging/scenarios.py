"""Test numbers: the last four digits of the recipient choose a reproducible outcome.

…0000  invalid recipient, rejected when sent (422)
…1111  accepted and sent, then delivery fails
…2222  unavailable (503) for the first FLAKY_FAILED_ATTEMPTS attempts, then accepted
…3333  rate limited (429 + Retry-After) on the first attempt, then accepted
…4444  delivered, never read
other  sent → delivered → read
"""

from enum import StrEnum

from .models import MessageStatus


class Scenario(StrEnum):
    NORMAL = "normal"
    INVALID_RECIPIENT = "invalid_recipient"
    DELIVERY_FAILS = "delivery_fails"
    FLAKY = "flaky"
    RATE_LIMITED = "rate_limited"
    NEVER_READ = "never_read"


_BY_SUFFIX = {
    "0000": Scenario.INVALID_RECIPIENT,
    "1111": Scenario.DELIVERY_FAILS,
    "2222": Scenario.FLAKY,
    "3333": Scenario.RATE_LIMITED,
    "4444": Scenario.NEVER_READ,
}


def scenario_for(recipient: str) -> Scenario:
    return _BY_SUFFIX.get(recipient[-4:], Scenario.NORMAL)


def next_status(current: MessageStatus, scenario: Scenario) -> MessageStatus | None:
    """The status after `current` in this scenario's lifecycle, or None once it is final."""
    if current == MessageStatus.ACCEPTED:
        return MessageStatus.SENT
    if current == MessageStatus.SENT:
        if scenario == Scenario.DELIVERY_FAILS:
            return MessageStatus.FAILED
        return MessageStatus.DELIVERED
    if current == MessageStatus.DELIVERED and scenario != Scenario.NEVER_READ:
        return MessageStatus.READ
    return None
