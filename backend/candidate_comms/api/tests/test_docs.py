import json
from io import StringIO

from django.core.management import call_command
from django.test import Client

from candidate_comms.core.exceptions import ErrorCode


def test_openapi_schema_is_served(client: Client) -> None:
    response = client.get("/api/schema/")

    assert response.status_code == 200
    assert b"Candidate Communication Platform API" in response.content


def test_swagger_ui_is_served(client: Client) -> None:
    response = client.get("/api/docs/")

    assert response.status_code == 200


def test_openapi_schema_generates_without_warnings() -> None:
    # The frontend's API types are generated from this schema, so warnings fail CI.
    call_command("spectacular", "--validate", "--fail-on-warn", stdout=StringIO())


def test_every_operation_documents_the_error_envelope() -> None:
    out = StringIO()
    call_command("spectacular", "--format", "openapi-json", stdout=out)
    schema = json.loads(out.getvalue())

    codes = schema["components"]["schemas"]["ErrorCodeEnum"]["enum"]
    assert codes == [code.value for code in ErrorCode]
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            assert "default" in operation["responses"], f"{method.upper()} {path}"
