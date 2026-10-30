import pytest
from django.test import Client

from simulator.conftest import SEND_URL, Scheduled, send_payload
from simulator.faults.services import faults_update

pytestmark = pytest.mark.django_db

FAULTS_URL = "/_demo/faults"


def test_faults_are_off_by_default(api_client: Client) -> None:
    data = api_client.get(FAULTS_URL).json()

    assert (data["outage"], data["failure_rate"], data["latency_ms"]) == (False, 0.0, 0)


def test_post_changes_only_the_given_faults(api_client: Client) -> None:
    api_client.post(FAULTS_URL, {"latency_ms": 200}, content_type="application/json")

    data = api_client.post(FAULTS_URL, {"outage": True}, content_type="application/json").json()

    assert (data["outage"], data["latency_ms"]) == (True, 200)


def test_post_validates_ranges(api_client: Client) -> None:
    response = api_client.post(FAULTS_URL, {"failure_rate": 2}, content_type="application/json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_outage_fails_every_call_and_reports_down(api_client: Client) -> None:
    faults_update(outage=True)

    send = api_client.post(SEND_URL, send_payload(), content_type="application/json")
    health = api_client.get("/health").json()

    assert send.status_code == 503
    assert send.json()["error"]["code"] == "gateway_unavailable"
    assert health == {"status": "down"}


def test_failure_rate_fails_calls_at_random(api_client: Client) -> None:
    faults_update(failure_rate=1.0)

    response = api_client.post(SEND_URL, send_payload(), content_type="application/json")

    assert response.status_code == 503
    assert api_client.get("/health").json() == {"status": "degraded"}


def test_latency_delays_provider_calls_only(
    api_client: Client, scheduled: Scheduled, monkeypatch: pytest.MonkeyPatch
) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("simulator.faults.middleware.asyncio.sleep", fake_sleep)
    faults_update(latency_ms=1500)

    response = api_client.post(SEND_URL, send_payload(), content_type="application/json")
    api_client.get("/health")

    assert response.status_code == 202
    assert sleeps == [1.5]
