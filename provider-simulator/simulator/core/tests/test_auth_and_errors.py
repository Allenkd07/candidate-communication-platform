import pytest
from django.conf import settings
from django.test import Client, override_settings

from simulator.conftest import SEND_URL, send_payload

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("authorization", [None, "Bearer wrong-key", "Basic abc"])
def test_calls_without_a_valid_api_key_are_unauthorized(authorization: str | None) -> None:
    headers = {"Authorization": authorization} if authorization else {}
    client = Client(headers=headers)

    response = client.post(SEND_URL, send_payload(), content_type="application/json")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_the_auth_scheme_is_case_insensitive() -> None:
    client = Client(headers={"Authorization": f"bearer {settings.SIMULATOR_API_KEY}"})

    assert client.get("/_demo/faults").status_code == 200


@override_settings(DEBUG=True)
@pytest.mark.parametrize("path", ["/v2/nothing", "/v1/messages/"])
def test_unknown_urls_answer_with_the_error_envelope(api_client: Client, path: str) -> None:
    response = api_client.get(path)

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not found."}}


def test_health_needs_no_api_key(client: Client) -> None:
    assert client.get("/health").status_code == 200
