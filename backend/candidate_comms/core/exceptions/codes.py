from enum import StrEnum


class ErrorCode(StrEnum):
    """Machine-readable error codes. The frontend maps each one to recruiter-facing copy."""

    VALIDATION_ERROR = "validation_error"
    BAD_REQUEST = "bad_request"
    PARSE_ERROR = "parse_error"
    NOT_AUTHENTICATED = "not_authenticated"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    NOT_ACCEPTABLE = "not_acceptable"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    THROTTLED = "throttled"
    CONFLICT = "conflict"
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    INVALID_WEBHOOK_SIGNATURE = "invalid_webhook_signature"
    INVALID_WEBHOOK_PAYLOAD = "invalid_webhook_payload"
    INTERNAL_ERROR = "internal_error"
