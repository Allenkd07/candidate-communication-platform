import json
from datetime import timedelta

import pytest
from django.utils import timezone
from pytest_django import DjangoCaptureOnCommitCallbacks

from candidate_comms.communications.models import EventSource, MessageEvent, MessageStatus
from candidate_comms.communications.services.delivery import Failure, message_apply_status
from candidate_comms.communications.state_machine import Transition
from candidate_comms.conftest import PublishedEvents
from candidate_comms.integrations.messaging.exceptions import (
    DeliveryFailedError,
    GatewayUnavailableError,
)

from .factories import MessageFactory

pytestmark = pytest.mark.django_db


def test_forward_status_is_applied_and_fills_implied_milestones() -> None:
    message = MessageFactory.create(status=MessageStatus.QUEUED)
    read_at = timezone.now() - timedelta(minutes=1)

    result = message_apply_status(
        message_id=message.id,
        status=MessageStatus.READ,
        source=EventSource.WEBHOOK,
        occurred_at=read_at,
    )

    message.refresh_from_db()
    assert result.transition == Transition.APPLY
    assert message.status == MessageStatus.READ
    assert message.sent_at == message.delivered_at == message.read_at == read_at
    assert MessageEvent.objects.get(message=message).applied is True


def test_duplicate_provider_event_is_recorded_once() -> None:
    message = MessageFactory.create(status=MessageStatus.SENT)

    def deliver() -> Transition:
        return message_apply_status(
            message_id=message.id,
            status=MessageStatus.DELIVERED,
            source=EventSource.WEBHOOK,
            gateway="simulator",
            provider_event_id="evt_1",
        ).transition

    first, second = deliver(), deliver()

    assert (first, second) == (Transition.APPLY, Transition.DUPLICATE)
    assert MessageEvent.objects.filter(message=message).count() == 1


def test_out_of_order_signal_is_logged_but_not_applied() -> None:
    message = MessageFactory.create(status=MessageStatus.READ)

    result = message_apply_status(
        message_id=message.id, status=MessageStatus.DELIVERED, source=EventSource.WEBHOOK
    )

    message.refresh_from_db()
    assert result.transition == Transition.STALE
    assert message.status == MessageStatus.READ
    assert MessageEvent.objects.get(message=message).applied is False


def test_failure_records_reason_and_retryability() -> None:
    message = MessageFactory.create(status=MessageStatus.SENT)

    message_apply_status(
        message_id=message.id,
        status=MessageStatus.FAILED,
        source=EventSource.WEBHOOK,
        failure=Failure.from_gateway_error(DeliveryFailedError()),
    )

    message.refresh_from_db()
    assert message.status == MessageStatus.FAILED
    assert message.failure_code == "delivery_failed"
    assert message.failure_reason == DeliveryFailedError.user_message
    assert message.is_retryable is True
    assert message.failed_at is not None


def test_exhausted_failure_uses_the_exhausted_copy() -> None:
    failure = Failure.from_gateway_error(GatewayUnavailableError(), retries_exhausted=True)

    assert failure.reason == GatewayUnavailableError.exhausted_message
    assert failure.is_retryable is True


def test_applied_change_is_published_after_commit(
    published_events: PublishedEvents,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    message = MessageFactory.create(status=MessageStatus.QUEUED)

    with django_capture_on_commit_callbacks(execute=True):
        message_apply_status(
            message_id=message.id, status=MessageStatus.SENT, source=EventSource.PLATFORM
        )

    [(_, raw)] = published_events.messages
    event = json.loads(raw)
    assert event["type"] == "message.status"
    assert event["data"]["message_id"] == str(message.id)
    assert event["data"]["status"] == "sent"


def test_ignored_signal_is_not_published(
    published_events: PublishedEvents,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    message = MessageFactory.create(status=MessageStatus.READ)

    with django_capture_on_commit_callbacks(execute=True):
        message_apply_status(
            message_id=message.id, status=MessageStatus.SENT, source=EventSource.WEBHOOK
        )

    assert published_events.messages == []
