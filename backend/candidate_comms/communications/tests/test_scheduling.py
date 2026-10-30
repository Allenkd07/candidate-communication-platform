import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone
from pytest_django import DjangoCaptureOnCommitCallbacks

from candidate_comms.candidates.tests.factories import CandidateFactory
from candidate_comms.communications.models import Message, MessageStatus
from candidate_comms.communications.services import dispatch, scheduling
from candidate_comms.communications.services.scheduling import scheduled_messages_release

pytestmark = pytest.mark.django_db


@pytest.fixture
def enqueued(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    sent: list[uuid.UUID] = []
    monkeypatch.setattr(dispatch, "message_enqueue_send", sent.append)
    monkeypatch.setattr(scheduling, "message_enqueue_send", sent.append)
    return sent


def schedule(client: Client, candidate_ids: list[uuid.UUID], when: str) -> dict[str, object]:
    payload = {
        "candidate_ids": [str(c) for c in candidate_ids],
        "body": "Hi {{first_name}}, see you tomorrow.",
        "scheduled_at": when,
    }
    response = client.post("/api/v1/messages/", payload, content_type="application/json")
    data: dict[str, object] = {"status_code": response.status_code, **response.json()}
    return data


def test_a_scheduled_send_waits_until_its_time(
    client: Client,
    enqueued: list[uuid.UUID],
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    candidate = CandidateFactory.create()
    when = timezone.now() + timedelta(hours=2)

    with django_capture_on_commit_callbacks(execute=True):
        data = schedule(client, [candidate.id], when.isoformat())

    message = Message.objects.get()
    assert data["status_code"] == 202
    assert message.status == MessageStatus.SCHEDULED
    assert message.scheduled_for == when
    assert enqueued == []
    assert scheduled_messages_release().released == 0


def test_due_messages_are_queued_and_sent_once(
    client: Client,
    enqueued: list[uuid.UUID],
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    candidate = CandidateFactory.create()
    schedule(client, [candidate.id], (timezone.now() + timedelta(minutes=5)).isoformat())
    Message.objects.update(scheduled_for=timezone.now() - timedelta(seconds=1))

    with django_capture_on_commit_callbacks(execute=True):
        first = scheduled_messages_release()
        second = scheduled_messages_release()

    message = Message.objects.get()
    assert (first.released, second.released) == (1, 0)
    assert message.status == MessageStatus.QUEUED
    assert enqueued == [message.id]


def test_a_deleted_candidates_message_fails_instead_of_sending(
    client: Client,
    enqueued: list[uuid.UUID],
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    candidate = CandidateFactory.create()
    schedule(client, [candidate.id], (timezone.now() + timedelta(minutes=5)).isoformat())
    Message.objects.update(scheduled_for=timezone.now() - timedelta(seconds=1))
    candidate.is_deleted = True
    candidate.save()

    with django_capture_on_commit_callbacks(execute=True):
        result = scheduled_messages_release()

    message = Message.objects.get()
    assert result.cancelled == 1
    assert message.status == MessageStatus.FAILED
    assert "deleted before the scheduled time" in message.failure_reason
    assert not message.is_retryable
    assert enqueued == []


@pytest.mark.parametrize(
    ("offset", "expected"),
    [(timedelta(seconds=10), "at least a minute"), (timedelta(days=31), "within the next 30")],
)
def test_the_time_must_be_in_range(client: Client, offset: timedelta, expected: str) -> None:
    candidate = CandidateFactory.create()

    data = schedule(client, [candidate.id], (timezone.now() + offset).isoformat())

    assert data["status_code"] == 400
    error = data["error"]
    assert isinstance(error, dict)
    assert expected in error["fields"]["scheduled_at"][0]
    assert not Message.objects.exists()
