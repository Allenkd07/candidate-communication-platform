"""Resend (email) adapter. Statuses arrive as Svix-signed webhooks and can be polled."""

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import requests

from ..base import (
    DeliveryStatus,
    GatewayHealth,
    HealthStatus,
    MessagingGateway,
    SendRequest,
    SendResult,
    StatusEvent,
)
from ..exceptions import (
    DeliveryFailedError,
    GatewayError,
    GatewayRejectedError,
    GatewayUnavailableError,
    InvalidRecipientError,
    RateLimitedError,
    WebhookPayloadError,
    WebhookVerificationError,
)

SIGNATURE_TOLERANCE_SECONDS = 300


class InvalidEmailError(InvalidRecipientError):
    user_message = "This email address can't receive messages. Check the address."


class EmailRejectedError(GatewayRejectedError):
    code = "email_rejected"
    user_message = "The email provider refused this message. Check the email setup."


class EmailBouncedError(DeliveryFailedError):
    code = "email_bounced"
    manually_retryable = False
    user_message = "The email bounced: the address may not exist or the inbox refused it."


# Resend event → our status. Events not listed (clicked, delayed, complained) change nothing.
_STATUSES = {
    "sent": DeliveryStatus.SENT,
    "delivered": DeliveryStatus.DELIVERED,
    "opened": DeliveryStatus.READ,
    "bounced": DeliveryStatus.FAILED,
}


class ResendGateway(MessagingGateway):
    name = "resend"
    label = "Email"
    channel = "email"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        sender: str,
        subject: str,
        webhook_secret: str,
        timeout: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._sender = sender
        self._subject = subject
        self._webhook_secret = webhook_secret
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {api_key}"

    def send(self, request: SendRequest) -> SendResult:
        payload = {
            "from": self._sender,
            "to": [request.recipient],
            "subject": self._subject,
            "text": request.body,
        }
        data = self._request(
            "POST", "/emails", json=payload, headers={"Idempotency-Key": request.idempotency_key}
        )
        try:
            return SendResult(provider_message_id=str(data["id"]))
        except KeyError as exc:
            raise GatewayRejectedError("Response has no email id") from exc

    def fetch_status(self, provider_message_id: str) -> StatusEvent | None:
        data = self._request("GET", f"/emails/{provider_message_id}")
        status = _STATUSES.get(str(data.get("last_event", "")))
        if status is None:
            return None
        return StatusEvent(
            provider_message_id=provider_message_id,
            status=status,
            occurred_at=datetime.now(UTC),
            error=EmailBouncedError() if status == DeliveryStatus.FAILED else None,
            raw=dict(data),
        )

    def health(self) -> GatewayHealth:
        try:
            self._request("GET", "/domains")
        except GatewayUnavailableError as exc:
            return GatewayHealth(status=HealthStatus.DOWN, detail=str(exc))
        except RateLimitedError as exc:
            return GatewayHealth(status=HealthStatus.DEGRADED, detail=str(exc))
        except GatewayError as exc:
            # A sending-only key can't list domains, but the answer proves Resend is reachable.
            if "restricted to only send" not in exc.detail:
                return GatewayHealth(status=HealthStatus.DOWN, detail=f"API key rejected: {exc}")
        return GatewayHealth(status=HealthStatus.OPERATIONAL)

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> list[StatusEvent]:
        self._verify_signature(headers, body)
        try:
            event = json.loads(body)
            status = _STATUSES.get(str(event["type"]).removeprefix("email."))
            if status is None:
                return []
            return [
                StatusEvent(
                    provider_message_id=str(event["data"]["email_id"]),
                    status=status,
                    occurred_at=_parse_timestamp(str(event["created_at"])),
                    provider_event_id=headers.get("svix-id"),
                    error=EmailBouncedError() if status == DeliveryStatus.FAILED else None,
                    raw=event,
                )
            ]
        except (KeyError, ValueError, TypeError) as exc:
            raise WebhookPayloadError(str(exc)) from exc

    def _verify_signature(self, headers: Mapping[str, str], body: bytes) -> None:
        """Svix scheme: base64 HMAC-SHA256 of "{id}.{timestamp}.{body}" with the decoded secret."""
        if not self._webhook_secret:
            raise WebhookVerificationError("No webhook secret configured")
        message_id = headers.get("svix-id", "")
        timestamp = headers.get("svix-timestamp", "")
        signatures = headers.get("svix-signature", "")
        if not message_id or not timestamp.isdigit() or not signatures:
            raise WebhookVerificationError("Missing or malformed signature headers")
        if abs(time.time() - int(timestamp)) > SIGNATURE_TOLERANCE_SECONDS:
            raise WebhookVerificationError("Signature timestamp outside the tolerance window")
        key = base64.b64decode(self._webhook_secret.removeprefix("whsec_"))
        signed = f"{message_id}.{timestamp}.".encode() + body
        expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
        candidates = [part.split(",", 1)[1] for part in signatures.split() if "," in part]
        if not any(hmac.compare_digest(expected, candidate) for candidate in candidates):
            raise WebhookVerificationError("Signature mismatch")

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._session.request(
                method, f"{self._base_url}{path}", timeout=self._timeout, **kwargs
            )
        except requests.RequestException as exc:
            raise GatewayUnavailableError(f"{type(exc).__name__}: {exc}") from exc
        try:
            data = response.json()
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        if response.ok:
            return data
        raise _error_for(response, data)


def _error_for(response: requests.Response, data: Mapping[str, Any]) -> GatewayError:
    detail = f"HTTP {response.status_code}: {data.get('message', response.reason)}"
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "")
        return RateLimitedError(
            detail, retry_after=float(retry_after) if retry_after.isdigit() else None
        )
    if response.status_code >= 500:
        return GatewayUnavailableError(detail)
    if response.status_code == 422:
        return InvalidEmailError(detail)
    if response.status_code in (401, 403):
        # An account or domain setup problem, not a bad address.
        return EmailRejectedError(detail)
    return GatewayRejectedError(detail)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
