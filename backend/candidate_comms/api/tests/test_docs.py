from django.test import Client


def test_openapi_schema_is_served(client: Client) -> None:
    response = client.get("/api/schema/")

    assert response.status_code == 200
    assert b"Candidate Communication Platform API" in response.content


def test_swagger_ui_is_served(client: Client) -> None:
    response = client.get("/api/docs/")

    assert response.status_code == 200
