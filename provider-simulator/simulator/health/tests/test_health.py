from django.test import Client


def test_health_reports_operational(client: Client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "operational"}
