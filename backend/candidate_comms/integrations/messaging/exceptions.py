"""Normalized gateway errors. Adapters translate vendor errors into these classes.

`retryable` means the send task retries automatically; `manually_retryable` means a
recruiter may retry once the automatic retries are exhausted or the failure was final.
"""


class GatewayError(Exception):
    code = "gateway_error"
    retryable = False
    manually_retryable = False
    user_message = "The provider rejected this message."
    # Shown instead of user_message once automatic retries are exhausted.
    exhausted_message = "Sending kept failing, so automatic retries stopped. Retry the message."

    def __init__(self, detail: str = "", *, retry_after: float | None = None) -> None:
        super().__init__(detail or self.user_message)
        self.detail = detail
        self.retry_after = retry_after


class InvalidRecipientError(GatewayError):
    code = "invalid_recipient"
    user_message = "This mobile number can't receive messages. Check the number."


class RateLimitedError(GatewayError):
    code = "rate_limited"
    retryable = True
    manually_retryable = True
    user_message = "Sending is temporarily throttled, retrying automatically."
    exhausted_message = "Sending stayed throttled, so automatic retries stopped. Retry the message."


class GatewayUnavailableError(GatewayError):
    code = "gateway_unavailable"
    retryable = True
    manually_retryable = True
    user_message = "The messaging service is unavailable right now. We'll keep retrying."
    exhausted_message = (
        "The messaging service stayed unavailable, so automatic retries stopped. Retry the message."
    )


class DeliveryFailedError(GatewayError):
    code = "delivery_failed"
    manually_retryable = True
    user_message = "Message couldn't be delivered to the handset."


class GatewayRejectedError(GatewayError):
    code = "gateway_rejected"
    user_message = "The provider rejected this message."


class WebhookVerificationError(Exception):
    """The webhook's signature or timestamp is invalid; the request must be rejected."""


class WebhookPayloadError(Exception):
    """The webhook is authentic but its body does not match the expected schema."""


ERRORS_BY_CODE: dict[str, type[GatewayError]] = {
    cls.code: cls
    for cls in (
        InvalidRecipientError,
        RateLimitedError,
        GatewayUnavailableError,
        DeliveryFailedError,
        GatewayRejectedError,
    )
}
