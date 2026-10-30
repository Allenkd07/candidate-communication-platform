import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_health_reports_operational(client: Client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "operational"}
