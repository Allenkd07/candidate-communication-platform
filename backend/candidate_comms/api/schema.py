"""OpenAPI schema additions that DRF views cannot describe themselves."""

from typing import Any

from candidate_comms.core.exceptions import ErrorCode

_ERROR_REF = "#/components/schemas/ErrorResponse"


def add_error_envelope(result: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Document the error envelope as every operation's default response.

    The custom exception handler renders all API errors in this shape, so the generated
    frontend types can map each `code` to recruiter-facing copy.
    """
    schemas = result.setdefault("components", {}).setdefault("schemas", {})
    schemas["ErrorCodeEnum"] = {"type": "string", "enum": [code.value for code in ErrorCode]}
    schemas["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "error": {
                "type": "object",
                "properties": {
                    "code": {"$ref": "#/components/schemas/ErrorCodeEnum"},
                    "message": {"type": "string"},
                    # Field path (e.g. "items.1.phone") → messages; empty for non-field errors.
                    "fields": {
                        "type": "object",
                        "additionalProperties": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "required": ["code", "message", "fields"],
            }
        },
        "required": ["error"],
    }

    for operations in result.get("paths", {}).values():
        for operation in operations.values():
            operation.setdefault("responses", {}).setdefault(
                "default",
                {
                    "description": "Error",
                    "content": {"application/json": {"schema": {"$ref": _ERROR_REF}}},
                },
            )
    return result
