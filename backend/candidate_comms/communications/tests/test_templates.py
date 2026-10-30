import uuid

import pytest
from django.test import Client

from candidate_comms.candidates.tests.factories import CandidateFactory
from candidate_comms.communications.models import Message, MessageTemplate
from candidate_comms.communications.services import dispatch

pytestmark = pytest.mark.django_db

URL = "/api/v1/templates/"
INVITE = {"name": "Interview invite", "body": "Hi {{first_name}}, this is {{full_name}}'s invite."}


def test_create_list_update_and_delete(client: Client) -> None:
    created = client.post(URL, INVITE, content_type="application/json")
    template_id = created.json()["id"]

    updated = client.put(
        f"{URL}{template_id}/",
        {"name": "  Interview   invite v2 ", "body": "Hello {{full_name}}"},
        content_type="application/json",
    )
    listed = client.get(URL).json()
    deleted = client.delete(f"{URL}{template_id}/")

    assert created.status_code == 201
    assert updated.json()["name"] == "Interview invite v2"
    assert [row["body"] for row in listed] == ["Hello {{full_name}}"]
    assert deleted.status_code == 204
    assert not MessageTemplate.objects.exists()


def test_names_are_unique_regardless_of_case(client: Client) -> None:
    client.post(URL, INVITE, content_type="application/json")

    response = client.post(
        URL, {**INVITE, "name": "INTERVIEW INVITE"}, content_type="application/json"
    )

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "duplicate_template"
    assert set(error["fields"]) == {"name"}


def test_unknown_placeholders_are_rejected(client: Client) -> None:
    response = client.post(
        URL,
        {"name": "Bad", "body": "Hi {{first_name}} {{salary}}"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "{{salary}}" in response.json()["error"]["fields"]["body"][0]


def test_placeholders_are_filled_in_per_recipient(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dispatch, "message_enqueue_send", lambda message_id: None)
    taylor = CandidateFactory.create(full_name="Taylor Swift")
    aarav = CandidateFactory.create(full_name="Aarav Sharma")
    payload = {"candidate_ids": [str(taylor.id), str(aarav.id)], "body": INVITE["body"]}

    response = client.post("/api/v1/messages/", payload, content_type="application/json")

    assert response.status_code == 202
    bodies = dict(Message.objects.values_list("candidate__full_name", "body"))
    assert bodies == {
        "Taylor Swift": "Hi Taylor, this is Taylor Swift's invite.",
        "Aarav Sharma": "Hi Aarav, this is Aarav Sharma's invite.",
    }


def test_a_message_too_long_once_filled_in_is_rejected(client: Client) -> None:
    candidate = CandidateFactory.create(full_name="Taylor " + "S" * 90)
    body = "x" * 985 + "{{full_name}}"
    payload = {"candidate_ids": [str(candidate.id)], "body": body}

    response = client.post("/api/v1/messages/", payload, content_type="application/json")

    assert response.status_code == 400
    assert "details filled in" in response.json()["error"]["fields"]["body"][0]
    assert not Message.objects.exists()


def test_unknown_template_is_not_found(client: Client) -> None:
    response = client.delete(f"{URL}{uuid.uuid4()}/")

    assert response.status_code == 404
