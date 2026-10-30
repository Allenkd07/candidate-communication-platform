import uuid

import pytest
from django.test import Client
from pytest_django import DjangoCaptureOnCommitCallbacks

from candidate_comms.candidates.tests.factories import CandidateFactory
from candidate_comms.communications.models import Message, MessageStatus
from candidate_comms.communications.services import dispatch, retry

from .factories import MessageBatchFactory, MessageFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def enqueued(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    sent: list[uuid.UUID] = []
    monkeypatch.setattr(dispatch, "message_enqueue_send", sent.append)
    monkeypatch.setattr(retry, "message_enqueue_send", sent.append)
    return sent


def failed(**kwargs: object) -> Message:
    return MessageFactory.create(
        status=MessageStatus.FAILED,
        is_retryable=True,
        failure_reason="Message couldn't be delivered to the handset.",
        **kwargs,
    )


def test_retry_sends_a_new_message_that_replaces_the_failed_one(
    client: Client,
    enqueued: list[uuid.UUID],
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    original = failed()

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(f"/api/v1/messages/{original.id}/retry/")

    assert response.status_code == 202
    [row] = response.json()["messages"]
    new = Message.objects.get(retry_of=original)
    assert row["id"] == str(new.id)
    assert row["status"] == "queued"
    assert row["retry_of_id"] == str(original.id)
    assert new.idempotency_key != original.idempotency_key
    assert enqueued == [new.id]


def test_history_keeps_both_attempts_and_only_the_new_one_can_be_retried(
    client: Client, enqueued: list[uuid.UUID]
) -> None:
    original = failed()
    client.post(f"/api/v1/messages/{original.id}/retry/")

    rows = client.get(f"/api/v1/candidates/{original.candidate.id}/messages/").json()["results"]

    assert [(row["status"], row["can_retry"]) for row in rows] == [
        ("queued", False),
        ("failed", False),
    ]


@pytest.mark.parametrize(
    "setup",
    ["not_retryable_failure", "not_failed", "already_retried", "candidate_deleted"],
)
def test_retry_is_refused_when_the_rules_do_not_allow_it(
    client: Client, enqueued: list[uuid.UUID], setup: str
) -> None:
    if setup == "not_retryable_failure":
        message = MessageFactory.create(status=MessageStatus.FAILED, is_retryable=False)
    elif setup == "not_failed":
        message = MessageFactory.create(status=MessageStatus.DELIVERED, is_retryable=True)
    elif setup == "already_retried":
        message = failed()
        client.post(f"/api/v1/messages/{message.id}/retry/")
        enqueued.clear()
    else:
        message = failed()
        message.candidate.is_deleted = True
        message.candidate.save()

    response = client.post(f"/api/v1/messages/{message.id}/retry/")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_retryable"
    assert enqueued == []


def test_retry_of_an_unknown_message_is_not_found(client: Client) -> None:
    response = client.post(f"/api/v1/messages/{uuid.uuid4()}/retry/")

    assert response.status_code == 404


def test_retry_failed_in_batch_retries_only_the_retryable_ones(
    client: Client, enqueued: list[uuid.UUID]
) -> None:
    batch = MessageBatchFactory.create()
    retryable = failed(batch=batch, candidate=CandidateFactory.create(full_name="Alpha One"))
    permanent = MessageFactory.create(
        batch=batch,
        candidate=CandidateFactory.create(full_name="Beta Two"),
        status=MessageStatus.FAILED,
        is_retryable=False,
    )
    MessageFactory.create(
        batch=batch, candidate=CandidateFactory.create(full_name="Gamma Three"), status="read"
    )

    response = client.post(f"/api/v1/batches/{batch.id}/retry-failed/")

    data = response.json()
    assert response.status_code == 202
    assert data["total"] == 3
    assert data["counts"]["queued"] == 1
    assert data["counts"]["failed"] == 1
    assert Message.objects.filter(retry_of=retryable).exists()
    assert not Message.objects.filter(retry_of=permanent).exists()

    again = client.post(f"/api/v1/batches/{batch.id}/retry-failed/")

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "not_retryable"


def test_a_retried_message_does_not_block_a_hard_delete(
    client: Client, enqueued: list[uuid.UUID]
) -> None:
    original = failed()
    client.post(f"/api/v1/messages/{original.id}/retry/")

    original.candidate.delete()

    assert not Message.objects.exists()
