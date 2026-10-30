import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone
from pytest_django import DjangoCaptureOnCommitCallbacks

from candidate_comms.candidates.tests.factories import CandidateFactory
from candidate_comms.communications.models import Message, MessageStatus
from candidate_comms.communications.services import dispatch

from .factories import MessageBatchFactory, MessageFactory

pytestmark = pytest.mark.django_db


def test_send_returns_202_with_every_recipient_queued(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    enqueued: list[uuid.UUID] = []
    monkeypatch.setattr(dispatch, "message_enqueue_send", enqueued.append)
    candidates = CandidateFactory.create_batch(3)
    payload = {"candidate_ids": [str(c.id) for c in candidates], "body": "Interview tomorrow?"}

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post("/api/v1/messages/", payload, content_type="application/json")

    assert response.status_code == 202
    data = response.json()
    assert data["total"] == 3
    assert data["counts"]["queued"] == 3
    assert {m["candidate"]["id"] for m in data["messages"]} == {str(c.id) for c in candidates}
    assert len(enqueued) == 3


def test_resending_with_the_same_key_returns_the_first_batch(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    enqueued: list[uuid.UUID] = []
    monkeypatch.setattr(dispatch, "message_enqueue_send", enqueued.append)
    candidates = CandidateFactory.create_batch(2)
    payload = {
        "candidate_ids": [str(c.id) for c in candidates],
        "body": "Interview tomorrow?",
        "idempotency_key": str(uuid.uuid4()),
    }

    with django_capture_on_commit_callbacks(execute=True):
        first = client.post("/api/v1/messages/", payload, content_type="application/json")
        repeat = client.post("/api/v1/messages/", payload, content_type="application/json")

    assert first.status_code == repeat.status_code == 202
    assert repeat.json()["id"] == first.json()["id"]
    assert Message.objects.count() == 2
    assert len(enqueued) == 2


def test_sends_without_a_key_are_independent(client: Client) -> None:
    candidate = CandidateFactory.create()
    payload = {"candidate_ids": [str(candidate.id)], "body": "Interview tomorrow?"}

    first = client.post("/api/v1/messages/", payload, content_type="application/json")
    second = client.post("/api/v1/messages/", payload, content_type="application/json")

    assert first.json()["id"] != second.json()["id"]
    assert Message.objects.count() == 2


def test_send_validates_input(client: Client) -> None:
    response = client.post(
        "/api/v1/messages/", {"candidate_ids": [], "body": ""}, content_type="application/json"
    )

    assert response.status_code == 400
    assert set(response.json()["error"]["fields"]) == {"candidate_ids", "body"}


def test_batch_summary_counts_each_status(client: Client) -> None:
    batch = MessageBatchFactory.create()
    for status in (MessageStatus.DELIVERED, MessageStatus.DELIVERED, MessageStatus.FAILED):
        MessageFactory.create(batch=batch, status=status)

    data = client.get(f"/api/v1/batches/{batch.id}/").json()

    assert data["total"] == 3
    assert data["counts"] == {
        "scheduled": 0,
        "queued": 0,
        "sent": 0,
        "delivered": 2,
        "read": 0,
        "failed": 1,
    }


def test_history_is_newest_first(client: Client) -> None:
    candidate = CandidateFactory.create()
    older = MessageFactory.create(candidate=candidate, body="First")
    Message.objects.filter(id=older.id).update(created_at=timezone.now() - timedelta(days=1))
    MessageFactory.create(candidate=candidate, body="Second")
    MessageFactory.create(body="Someone else's")

    data = client.get(f"/api/v1/candidates/{candidate.id}/messages/").json()

    assert [m["body"] for m in data["results"]] == ["Second", "First"]


def test_history_of_unknown_candidate_is_not_found(client: Client) -> None:
    response = client.get(f"/api/v1/candidates/{uuid.uuid4()}/messages/")

    assert response.status_code == 404


def test_a_channel_without_a_provider_is_refused(client: Client) -> None:
    candidate = CandidateFactory.create()
    payload = {"candidate_ids": [str(candidate.id)], "body": "Hello", "channel": "email"}

    response = client.post("/api/v1/messages/", payload, content_type="application/json")

    assert response.status_code == 400
    assert set(response.json()["error"]["fields"]) == {"channel"}
    assert not Message.objects.exists()


def test_email_messages_go_to_the_candidates_email(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dispatch, "message_enqueue_send", lambda message_id: None)
    monkeypatch.setattr(
        dispatch,
        "default_gateway_name",
        lambda channel: "resend" if channel == "email" else "simulator",
    )
    candidate = CandidateFactory.create(email="taylor@example.com")
    payload = {"candidate_ids": [str(candidate.id)], "body": "Hello", "channel": "email"}

    response = client.post("/api/v1/messages/", payload, content_type="application/json")

    message = Message.objects.get()
    assert response.status_code == 202
    assert (message.channel, message.gateway, message.recipient) == (
        "email",
        "resend",
        "taylor@example.com",
    )
