import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_health_reports_operational(client: Client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "operational"}


def test_the_base_url_describes_the_service(client: Client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Provider simulator"
    assert data["endpoints"]["health"] == "GET /health"
