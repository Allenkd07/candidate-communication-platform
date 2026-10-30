import pytest
from django.test import Client
from pytest_django import DjangoCaptureOnCommitCallbacks

from simulator.conftest import SEND_URL, Scheduled, send_payload
from simulator.messaging.models import Message, MessageStatus

pytestmark = pytest.mark.django_db


def test_send_accepts_the_message_and_schedules_its_lifecycle(
    api_client: Client,
    scheduled: Scheduled,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.post(SEND_URL, send_payload(), content_type="application/json")

    assert response.status_code == 202
    message = Message.objects.get()
    assert response.json() == {"id": message.id, "status": "accepted"}
    assert message.id.startswith("SM")
    assert message.status == MessageStatus.ACCEPTED
    assert scheduled.steps == [message.id]


def test_a_repeated_idempotency_key_returns_the_original_message(
    api_client: Client, scheduled: Scheduled
) -> None:
    first = api_client.post(SEND_URL, send_payload(), content_type="application/json")
    second = api_client.post(SEND_URL, send_payload(), content_type="application/json")

    assert second.status_code == 202
    assert second.json() == first.json()
    assert second.headers["Idempotent-Replayed"] == "true"
    assert Message.objects.count() == 1


def test_replaying_a_message_still_accepted_queues_its_lifecycle_again(
    api_client: Client, scheduled: Scheduled
) -> None:
    # The first request saved the message but failed to queue its lifecycle.
    message = Message.objects.create(
        idempotency_key="key-1", to="+919845012345", body="Hi", callback_url="http://api:8000/"
    )

    api_client.post(SEND_URL, send_payload(body="Hi"), content_type="application/json")

    assert scheduled.steps == [message.id]


def test_body_whitespace_is_kept(api_client: Client, scheduled: Scheduled) -> None:
    body = "  Hi\n-- Recruiter\n"

    api_client.post(SEND_URL, send_payload(body=body), content_type="application/json")

    assert Message.objects.get().body == body


def test_reusing_a_key_for_a_different_message_is_a_conflict(
    api_client: Client, scheduled: Scheduled
) -> None:
    api_client.post(SEND_URL, send_payload(), content_type="application/json")

    response = api_client.post(
        SEND_URL, send_payload(body="Something else"), content_type="application/json"
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_key_reused"


@pytest.mark.parametrize("to", ["+919876500000", "9845012345", "+91-98450"])
def test_invalid_recipients_are_rejected(api_client: Client, to: str) -> None:
    response = api_client.post(SEND_URL, send_payload(to=to), content_type="application/json")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_recipient"
    assert not Message.objects.exists()


def test_flaky_number_fails_twice_per_key_then_accepts(
    api_client: Client, scheduled: Scheduled
) -> None:
    payload = send_payload(to="+919876522222")

    statuses = [
        api_client.post(SEND_URL, payload, content_type="application/json").status_code
        for _ in range(3)
    ]
    other_key = api_client.post(
        SEND_URL, {**payload, "idempotency_key": "key-2"}, content_type="application/json"
    )

    assert statuses == [503, 503, 202]
    assert other_key.status_code == 503


def test_rate_limited_number_throttles_the_first_attempt(
    api_client: Client, scheduled: Scheduled
) -> None:
    payload = send_payload(to="+919876533333")

    throttled = api_client.post(SEND_URL, payload, content_type="application/json")
    retried = api_client.post(SEND_URL, payload, content_type="application/json")

    assert throttled.status_code == 429
    assert throttled.headers["Retry-After"] == "5"
    assert throttled.json()["error"]["code"] == "rate_limited"
    assert retried.status_code == 202


def test_send_validates_the_request(api_client: Client) -> None:
    response = api_client.post(
        SEND_URL, send_payload(callback_url="not-a-url"), content_type="application/json"
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "invalid_request", "message": "callback_url: Enter an http(s) URL."}
    }


def test_status_lookup_returns_the_current_status(api_client: Client) -> None:
    message = Message.objects.create(
        idempotency_key="key-1",
        to="+919876511111",
        body="Hi",
        callback_url="http://api:8000/",
        status=MessageStatus.FAILED,
        error_code="delivery_failed",
        error_message="Not delivered.",
    )

    data = api_client.get(f"{SEND_URL}/{message.id}").json()

    assert data["id"] == message.id
    assert data["status"] == "failed"
    assert data["error"] == {"code": "delivery_failed", "message": "Not delivered."}
    assert "updated_at" in data


def test_status_lookup_of_an_unknown_message_is_not_found(api_client: Client) -> None:
    response = api_client.get(f"{SEND_URL}/SMunknown")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
