import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from pytest_django import DjangoCaptureOnCommitCallbacks

from simulator.conftest import Scheduled
from simulator.messaging.models import Message, MessageStatus, WebhookEvent
from simulator.messaging.services import message_advance

pytestmark = pytest.mark.django_db


def _message(to: str) -> Message:
    return Message.objects.create(
        idempotency_key=f"key-{to}", to=to, body="Hi", callback_url="http://api:8000/"
    )


def _run_lifecycle(
    message: Message, captured: DjangoCaptureOnCommitCallbacks
) -> list[MessageStatus]:
    """Advance until the message is final; returns the status of every step."""
    statuses: list[MessageStatus] = []
    while True:
        message.refresh_from_db()
        with captured(execute=True):
            event = message_advance(
                message_id=message.id, from_status=MessageStatus(message.status)
            )
        if event is None:
            return statuses
        statuses.append(MessageStatus(event.status))


@pytest.mark.parametrize(
    ("to", "expected"),
    [
        ("+919845012345", ["sent", "delivered", "read"]),
        ("+919876511111", ["sent", "failed"]),
        ("+919876544444", ["sent", "delivered"]),
    ],
)
def test_lifecycle_follows_the_test_number_scenario(
    to: str,
    expected: list[str],
    scheduled: Scheduled,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    message = _message(to)

    statuses = _run_lifecycle(message, django_capture_on_commit_callbacks)

    message.refresh_from_db()
    assert statuses == expected
    assert message.status == expected[-1]
    assert list(message.events.values_list("status", flat=True)) == expected
    # One webhook per step; another step is scheduled for every step except the last.
    assert len(scheduled.webhooks) == len(expected)
    assert scheduled.steps == [message.id] * (len(expected) - 1)


def test_failed_delivery_records_the_carrier_error(
    scheduled: Scheduled, django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks
) -> None:
    message = _message("+919876511111")

    _run_lifecycle(message, django_capture_on_commit_callbacks)

    message.refresh_from_db()
    assert message.error_code == "delivery_failed"
    assert message.error_message


def test_a_repeated_step_does_not_skip_ahead(
    scheduled: Scheduled, django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks
) -> None:
    message = _message("+919845012345")

    with django_capture_on_commit_callbacks(execute=True):
        first = message_advance(message_id=message.id, from_status=MessageStatus.ACCEPTED)
        # A redelivered task for the same step.
        again = message_advance(message_id=message.id, from_status=MessageStatus.ACCEPTED)

    message.refresh_from_db()
    assert first is not None
    assert again is None
    assert message.status == MessageStatus.SENT
    assert len(scheduled.steps) == 1


def test_a_message_has_one_event_per_status() -> None:
    message = _message("+919845012345")
    WebhookEvent.objects.create(
        message=message, status=MessageStatus.SENT, occurred_at=timezone.now()
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        WebhookEvent.objects.create(
            message=message, status=MessageStatus.SENT, occurred_at=timezone.now()
        )
