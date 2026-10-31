import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from candidate_comms.candidates import services
from candidate_comms.candidates.models import Candidate
from candidate_comms.communications.models import Message, MessageStatus
from candidate_comms.communications.tests.factories import MessageFactory

from .factories import CandidateFactory

pytestmark = pytest.mark.django_db

LIST_URL = "/api/v1/candidates/"
NEW_CANDIDATE = {
    "full_name": " Taylor  Swift ",
    "phone": "98450 12345",
    "email": "Taylor@Example.com",
}


def test_create_normalizes_and_returns_the_candidate(client: Client) -> None:
    response = client.post(LIST_URL, NEW_CANDIDATE, content_type="application/json")

    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Taylor Swift"
    assert data["phone"] == "+919845012345"
    assert data["email"] == "taylor@example.com"
    assert len(data["code"]) == 6
    assert data["code"].isalnum()


def test_create_reports_field_errors(client: Client) -> None:
    payload = {"full_name": "T", "phone": "123", "email": "nope"}

    response = client.post(LIST_URL, payload, content_type="application/json")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert set(error["fields"]) == {"full_name", "phone", "email"}


def test_create_rejects_a_duplicate_phone(client: Client) -> None:
    CandidateFactory.create(phone="+919845012345")

    response = client.post(LIST_URL, NEW_CANDIDATE, content_type="application/json")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "duplicate_candidate"
    assert error["message"] == "A candidate with this mobile number already exists."
    assert set(error["fields"]) == {"phone"}


def test_create_rejects_a_duplicate_email_regardless_of_case(client: Client) -> None:
    CandidateFactory.create(email="taylor@example.com")

    response = client.post(LIST_URL, NEW_CANDIDATE, content_type="application/json")

    assert response.status_code == 409
    assert set(response.json()["error"]["fields"]) == {"email"}


def test_list_is_newest_first_and_paginated(client: Client) -> None:
    candidates = CandidateFactory.create_batch(12)

    response = client.get(LIST_URL, {"page_size": 5, "page": 1})

    data = response.json()
    assert response.status_code == 200
    assert data["count"] == 12
    assert [row["id"] for row in data["results"]] == [str(c.id) for c in reversed(candidates)][:5]
    assert data["next"] is not None


def test_list_shows_the_latest_message(client: Client) -> None:
    candidate = CandidateFactory.create()
    older = MessageFactory.create(candidate=candidate, status=MessageStatus.READ)
    Message.objects.filter(id=older.id).update(created_at=timezone.now() - timedelta(days=2))
    MessageFactory.create(
        candidate=candidate,
        status=MessageStatus.FAILED,
        body="Latest",
        failure_reason="Message couldn't be delivered to the handset.",
    )
    CandidateFactory.create()

    rows = {row["id"]: row for row in client.get(LIST_URL).json()["results"]}

    row = rows[str(candidate.id)]
    assert row["last_message_status"] == "failed"
    assert row["last_message_body"] == "Latest"
    assert row["last_message_failure_reason"] == "Message couldn't be delivered to the handset."
    assert row["last_message_at"] is not None
    assert [r["last_message_status"] for r in rows.values() if r["id"] != str(candidate.id)] == [
        None
    ]


@pytest.mark.parametrize("search", ["swift", "TAYLOR@", "98450 12345", "a1b2c3", "a1b"])
def test_search_matches_name_email_phone_digits_and_code(client: Client, search: str) -> None:
    taylor = CandidateFactory.create(
        full_name="Taylor Swift", phone="+919845012345", email="taylor@example.com", code="A1B2C3"
    )
    CandidateFactory.create(full_name="Someone Else", phone="+917012345678")

    results = client.get(LIST_URL, {"search": search}).json()["results"]

    assert [row["id"] for row in results] == [str(taylor.id)]


@pytest.mark.parametrize("search", ["b2c", "a1"])
def test_search_ignores_mid_and_short_id_fragments(client: Client, search: str) -> None:
    CandidateFactory.create(full_name="Taylor Swift", email="taylor@example.com", code="A1B2C3")

    results = client.get(LIST_URL, {"search": search}).json()["results"]

    assert results == []


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"name": "tay"}, ["taylor"]),
        ({"phone": "98450 12"}, ["taylor"]),
        ({"code": "b2c"}, ["taylor"]),
        ({"status": ["failed"]}, ["aarav"]),
        ({"status": ["read", "none"]}, ["taylor", "meera"]),
        ({"name": "a", "status": ["none"]}, ["meera"]),
    ],
)
def test_column_filters(
    client: Client, params: dict[str, str | list[str]], expected: list[str]
) -> None:
    people = {
        "taylor": CandidateFactory.create(
            full_name="Taylor Swift", phone="+919845012345", code="A1B2C3"
        ),
        "aarav": CandidateFactory.create(full_name="Aarav Sharma", phone="+917012345678"),
        "meera": CandidateFactory.create(full_name="Meera Kapoor", phone="+918800765432"),
    }
    MessageFactory.create(candidate=people["taylor"], status=MessageStatus.READ)
    MessageFactory.create(candidate=people["aarav"], status=MessageStatus.FAILED)

    results = client.get(LIST_URL, params).json()["results"]

    ids = {str(candidate.id): key for key, candidate in people.items()}
    assert sorted(ids[row["id"]] for row in results) == sorted(expected)


def test_last_message_date_range_uses_the_latest_message(client: Client) -> None:
    now = timezone.now()
    recent = CandidateFactory.create()
    MessageFactory.create(candidate=recent)
    earlier = CandidateFactory.create()
    old_message = MessageFactory.create(candidate=earlier)
    Message.objects.filter(id=old_message.id).update(created_at=now - timedelta(days=5))
    CandidateFactory.create()

    def ids(params: dict[str, str]) -> list[str]:
        return [row["id"] for row in client.get(LIST_URL, params).json()["results"]]

    since_yesterday = {"last_message_after": (now - timedelta(days=1)).isoformat()}
    until_yesterday = {"last_message_before": (now - timedelta(days=1)).isoformat()}
    assert ids(since_yesterday) == [str(recent.id)]
    assert ids(until_yesterday) == [str(earlier.id)]


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("", ["meera", "aarav", "taylor"]),
        ("name", ["aarav", "meera", "taylor"]),
        ("-name", ["taylor", "meera", "aarav"]),
        ("phone", ["aarav", "meera", "taylor"]),
        ("code", ["taylor", "aarav", "meera"]),
        ("-code", ["meera", "aarav", "taylor"]),
        ("last_message", ["taylor", "aarav", "meera"]),
        ("-last_message", ["aarav", "taylor", "meera"]),
        ("status", ["taylor", "aarav", "meera"]),
        ("-status", ["aarav", "taylor", "meera"]),
    ],
)
def test_sort(client: Client, sort: str, expected: list[str]) -> None:
    now = timezone.now()
    people = {
        "taylor": CandidateFactory.create(
            full_name="taylor Swift", phone="+919845012345", code="A00001"
        ),
        "aarav": CandidateFactory.create(
            full_name="Aarav Sharma", phone="+917012345678", code="B00001"
        ),
        "meera": CandidateFactory.create(
            full_name="Meera Kapoor", phone="+918800765432", code="C00001"
        ),
    }
    read = MessageFactory.create(candidate=people["taylor"], status=MessageStatus.READ)
    Message.objects.filter(id=read.id).update(created_at=now - timedelta(days=1))
    MessageFactory.create(candidate=people["aarav"], status=MessageStatus.FAILED)

    results = client.get(LIST_URL, {"sort": sort}).json()["results"]

    ids = {str(candidate.id): key for key, candidate in people.items()}
    assert [ids[row["id"]] for row in results] == expected


def test_filters_reject_bad_values(client: Client) -> None:
    now = timezone.now()
    reversed_range = {
        "last_message_after": now.isoformat(),
        "last_message_before": (now - timedelta(days=1)).isoformat(),
    }

    bad_status = client.get(LIST_URL, {"status": "unknown"})
    bad_phone = client.get(LIST_URL, {"phone": "abc"})
    bad_range = client.get(LIST_URL, reversed_range)
    bad_sort = client.get(LIST_URL, {"sort": "created_at"})

    assert bad_status.status_code == bad_phone.status_code == bad_range.status_code == 400
    assert bad_sort.status_code == 400
    assert set(bad_range.json()["error"]["fields"]) == {"last_message_before"}


def test_detail_and_unknown_candidate(client: Client) -> None:
    candidate = CandidateFactory.create()

    found = client.get(f"{LIST_URL}{candidate.id}/")
    missing = client.get(f"{LIST_URL}{uuid.uuid4()}/")

    assert found.json()["code"] == candidate.code
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_delete_hides_the_candidate_and_keeps_their_history(client: Client) -> None:
    message = MessageFactory.create()
    candidate_url = f"{LIST_URL}{message.candidate.id}/"

    response = client.delete(candidate_url)

    assert response.status_code == 204
    assert client.get(candidate_url).status_code == 404
    assert client.get(LIST_URL).json()["count"] == 0
    assert Candidate.all_objects.get(id=message.candidate.id).is_deleted is True
    assert Message.objects.filter(id=message.id).exists()


def test_a_deleted_candidate_can_be_added_again(client: Client) -> None:
    first = client.post(LIST_URL, NEW_CANDIDATE, content_type="application/json").json()
    client.delete(f"{LIST_URL}{first['id']}/")

    second = client.post(LIST_URL, NEW_CANDIDATE, content_type="application/json")

    assert second.status_code == 201
    assert second.json()["code"] != first["code"]


def test_bulk_delete_ignores_ids_that_no_longer_exist(client: Client) -> None:
    keep, *remove = CandidateFactory.create_batch(3)
    ids = [str(c.id) for c in remove] + [str(uuid.uuid4())]

    response = client.post(
        f"{LIST_URL}bulk-delete/", {"candidate_ids": ids}, content_type="application/json"
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    assert list(Candidate.objects.values_list("id", flat=True)) == [keep.id]


def test_bulk_delete_requires_ids(client: Client) -> None:
    response = client.post(
        f"{LIST_URL}bulk-delete/", {"candidate_ids": []}, content_type="application/json"
    )

    assert response.status_code == 400
    assert "candidate_ids" in response.json()["error"]["fields"]


def test_create_retries_when_a_concurrent_request_took_the_code(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    CandidateFactory.create(code="AAAAAA")
    codes = iter(["AAAAAA", "BBBBBB"])
    monkeypatch.setattr(services, "_generate_code", lambda: next(codes))

    response = client.post(LIST_URL, NEW_CANDIDATE, content_type="application/json")

    assert response.status_code == 201
    assert response.json()["code"] == "BBBBBB"
