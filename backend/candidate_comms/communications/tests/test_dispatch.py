import uuid

import pytest
from celery.exceptions import Retry
from django.test import override_settings
from pytest_django import DjangoCaptureOnCommitCallbacks

from candidate_comms.candidates.tests.factories import CandidateFactory
from candidate_comms.communications.models import Channel, Message, MessageStatus
from candidate_comms.communications.services import dispatch
from candidate_comms.communications.services.dispatch import (
    batch_create,
    message_send_attempt,
    retry_delay_seconds,
)
from candidate_comms.communications.tasks import send_message
from candidate_comms.conftest import FakeGateway
from candidate_comms.core.exceptions import ApplicationError
from candidate_comms.integrations.messaging.exceptions import (
    GatewayUnavailableError,
    InvalidRecipientError,
    RateLimitedError,
)

from .factories import MessageFactory

pytestmark = pytest.mark.django_db


def test_batch_create_queues_one_message_and_one_task_per_unique_candidate(
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    enqueued: list[uuid.UUID] = []
    monkeypatch.setattr(dispatch, "message_enqueue_send", enqueued.append)
    first, second = CandidateFactory.create(), CandidateFactory.create()

    with django_capture_on_commit_callbacks(execute=True):
        batch = batch_create(
            candidate_ids=[first.id, second.id, first.id], body="  Hi there  ", channel=Channel.SMS
        )

    messages = list(batch.messages.all())
    assert len(messages) == 2
    assert {message.status for message in messages} == {MessageStatus.QUEUED}
    assert {message.body for message in messages} == {"Hi there"}
    assert {message.recipient for message in messages} == {first.phone, second.phone}
    assert sorted(enqueued) == sorted(message.id for message in messages)


def test_nothing_is_enqueued_when_the_transaction_does_not_commit(
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    candidate = CandidateFactory.create()

    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        batch_create(candidate_ids=[candidate.id], body="Hi", channel=Channel.SMS)

    assert len(callbacks) == 1  # Deferred until commit, never run inline.


def test_batch_create_rejects_unknown_candidates() -> None:
    candidate = CandidateFactory.create()
    unknown = uuid.uuid4()

    with pytest.raises(ApplicationError) as exc_info:
        batch_create(candidate_ids=[candidate.id, unknown], body="Hi", channel=Channel.SMS)

    assert exc_info.value.status_code == 404
    assert exc_info.value.fields == {"candidate_ids": [str(unknown)]}
    assert not Message.objects.exists()


@pytest.mark.parametrize("body", ["", "   ", "x" * 1001])
def test_batch_create_rejects_invalid_bodies(body: str) -> None:
    candidate = CandidateFactory.create()

    with pytest.raises(ApplicationError) as exc_info:
        batch_create(candidate_ids=[candidate.id], body=body, channel=Channel.SMS)

    assert "body" in exc_info.value.fields


def test_send_attempt_marks_message_sent(fake_gateway: FakeGateway) -> None:
    message = MessageFactory.create()

    result = message_send_attempt(message_id=message.id)

    message.refresh_from_db()
    assert result.sent is True
    assert message.status == MessageStatus.SENT
    assert message.attempt_count == 1
    assert message.provider_message_id == f"prov-{message.idempotency_key}"
    [request] = fake_gateway.sent
    assert request.idempotency_key == str(message.idempotency_key)
    assert request.callback_url.endswith("/api/v1/webhooks/simulator/")


def test_permanent_error_fails_the_message_without_retry(fake_gateway: FakeGateway) -> None:
    fake_gateway.send_outcomes = [InvalidRecipientError("HTTP 422")]
    message = MessageFactory.create()

    result = message_send_attempt(message_id=message.id)

    message.refresh_from_db()
    assert result.retry_error is None
    assert message.status == MessageStatus.FAILED
    assert message.failure_code == "invalid_recipient"
    assert message.failure_reason == InvalidRecipientError.user_message
    assert message.is_retryable is False


def test_transient_error_leaves_message_queued_for_retry(fake_gateway: FakeGateway) -> None:
    fake_gateway.send_outcomes = [GatewayUnavailableError("timeout")]
    message = MessageFactory.create()

    result = message_send_attempt(message_id=message.id)

    message.refresh_from_db()
    assert isinstance(result.retry_error, GatewayUnavailableError)
    assert message.status == MessageStatus.QUEUED


def test_send_attempt_skips_messages_that_are_no_longer_queued(fake_gateway: FakeGateway) -> None:
    message = MessageFactory.create(status=MessageStatus.SENT)

    result = message_send_attempt(message_id=message.id)

    assert result.sent is False
    assert fake_gateway.sent == []


def test_task_retries_with_the_same_idempotency_key_until_success(
    fake_gateway: FakeGateway,
) -> None:
    fake_gateway.send_outcomes = [GatewayUnavailableError(), GatewayUnavailableError(), None]
    message = MessageFactory.create()

    # Each apply() stands in for one delivery of the task; Retry asks for another.
    for retries in range(2):
        with pytest.raises(Retry):
            send_message.apply(args=[str(message.id)], retries=retries)
        message.refresh_from_db()
        assert message.status == MessageStatus.QUEUED
    send_message.apply(args=[str(message.id)], retries=2)

    message.refresh_from_db()
    assert message.status == MessageStatus.SENT
    assert message.attempt_count == 3
    assert {request.idempotency_key for request in fake_gateway.sent} == {
        str(message.idempotency_key)
    }


def test_task_fails_the_message_once_retries_are_exhausted(fake_gateway: FakeGateway) -> None:
    fake_gateway.send_outcomes = [GatewayUnavailableError()] * 10
    message = MessageFactory.create()

    for retries in range(send_message.max_retries):
        with pytest.raises(Retry):
            send_message.apply(args=[str(message.id)], retries=retries)
    send_message.apply(args=[str(message.id)], retries=send_message.max_retries)

    message.refresh_from_db()
    assert message.status == MessageStatus.FAILED
    assert message.attempt_count == send_message.max_retries + 1
    assert message.failure_reason == GatewayUnavailableError.exhausted_message
    assert message.is_retryable is True


@override_settings(MESSAGE_RETRY_BASE_DELAY_SECONDS=2.0, MESSAGE_RETRY_MAX_DELAY_SECONDS=60.0)
def test_retry_delay_honours_retry_after_up_to_the_cap() -> None:
    assert retry_delay_seconds(retries=0, error=RateLimitedError(retry_after=7)) == 7
    assert retry_delay_seconds(retries=0, error=RateLimitedError(retry_after=600)) == 60


@override_settings(MESSAGE_RETRY_BASE_DELAY_SECONDS=2.0, MESSAGE_RETRY_MAX_DELAY_SECONDS=60.0)
@pytest.mark.parametrize(("retries", "ceiling"), [(0, 2.0), (1, 4.0), (3, 16.0), (10, 60.0)])
def test_retry_delay_backs_off_exponentially_with_jitter(retries: int, ceiling: float) -> None:
    delays = [
        retry_delay_seconds(retries=retries, error=GatewayUnavailableError()) for _ in range(50)
    ]

    assert all(1.0 <= delay <= ceiling for delay in delays)
