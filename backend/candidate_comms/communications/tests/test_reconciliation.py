import uuid
from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from pytest_django import DjangoCaptureOnCommitCallbacks

from candidate_comms.communications.models import MessageStatus
from candidate_comms.communications.services import reconciliation
from candidate_comms.communications.services.reconciliation import stale_messages_reconcile
from candidate_comms.conftest import FakeGateway
from candidate_comms.integrations.messaging.base import DeliveryStatus, StatusEvent

from .factories import MessageFactory

pytestmark = pytest.mark.django_db


def _ago(seconds: int) -> datetime:
    return timezone.now() - timedelta(seconds=seconds)


def test_stale_sent_message_is_updated_from_the_gateway(fake_gateway: FakeGateway) -> None:
    message = MessageFactory.create(
        status=MessageStatus.SENT, provider_message_id="prov-1", status_changed_at=_ago(3600)
    )
    fake_gateway.statuses["prov-1"] = StatusEvent(
        provider_message_id="prov-1", status=DeliveryStatus.DELIVERED, occurred_at=_ago(60)
    )

    result = stale_messages_reconcile()

    message.refresh_from_db()
    assert (result.checked, result.updated) == (1, 1)
    assert message.status == MessageStatus.DELIVERED


def test_recent_sent_messages_are_left_alone(fake_gateway: FakeGateway) -> None:
    MessageFactory.create(
        status=MessageStatus.SENT, provider_message_id="prov-1", status_changed_at=_ago(5)
    )

    assert stale_messages_reconcile().checked == 0


def test_stale_queued_message_is_re_enqueued_once(
    fake_gateway: FakeGateway,
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    enqueued: list[uuid.UUID] = []
    monkeypatch.setattr(reconciliation, "message_enqueue_send", enqueued.append)
    message = MessageFactory.create(status=MessageStatus.QUEUED, status_changed_at=_ago(3600))

    with django_capture_on_commit_callbacks(execute=True):
        first = stale_messages_reconcile()
        second = stale_messages_reconcile()

    assert (first.requeued, second.requeued) == (1, 0)
    assert enqueued == [message.id]


def test_stale_queued_message_out_of_attempts_is_failed(
    fake_gateway: FakeGateway,
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    enqueued: list[uuid.UUID] = []
    monkeypatch.setattr(reconciliation, "message_enqueue_send", enqueued.append)
    message = MessageFactory.create(
        status=MessageStatus.QUEUED, status_changed_at=_ago(3600), attempt_count=5
    )

    with django_capture_on_commit_callbacks(execute=True):
        result = stale_messages_reconcile()

    message.refresh_from_db()
    assert (result.requeued, result.abandoned) == (0, 1)
    assert enqueued == []
    assert message.status == MessageStatus.FAILED
    assert message.failure_code == "send_attempts_exhausted"
    assert message.is_retryable is True
