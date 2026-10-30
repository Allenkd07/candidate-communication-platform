"""Adapter for the provider simulator (provider-simulator/), called over HTTP like any vendor.

Wire contract:
    POST {base}/v1/messages           {to, body, idempotency_key, callback_url} → 202 {id, status}
    GET  {base}/v1/messages/{id}      → {id, status, updated_at, error}
    GET  {base}/health                → {status: operational | degraded | down}
    Errors                            → {"error": {"code", "message"}}; 429 carries Retry-After
    Webhook to callback_url           {event_id, message_id, idempotency_key, status, occurred_at,
                                       error}, signed in X-Simulator-Signature: t=<unix>,v1=<hex>
                                       where v1 = HMAC-SHA256(secret, f"{t}.{raw body}")
"""

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
    ERRORS_BY_CODE,
    GatewayError,
    GatewayRejectedError,
    GatewayUnavailableError,
    InvalidRecipientError,
    RateLimitedError,
    WebhookPayloadError,
    WebhookVerificationError,
)

SIGNATURE_HEADER = "X-Simulator-Signature"
SIGNATURE_TOLERANCE_SECONDS = 300
# Simulator status "accepted" means received but not yet handed to the carrier.
_REPORTABLE_STATUSES = {status.value for status in DeliveryStatus}


class SimulatorGateway(MessagingGateway):
    name = "simulator"

    def __init__(self, *, base_url: str, api_key: str, webhook_secret: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._webhook_secret = webhook_secret.encode()
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {api_key}"

    def send(self, request: SendRequest) -> SendResult:
        payload = {
            "to": request.recipient,
            "body": request.body,
            "idempotency_key": request.idempotency_key,
            "callback_url": request.callback_url,
        }
        data = self._request("POST", "/v1/messages", json=payload)
        try:
            return SendResult(provider_message_id=str(data["id"]))
        except KeyError as exc:
            raise GatewayRejectedError("Response has no message id") from exc

    def fetch_status(self, provider_message_id: str) -> StatusEvent | None:
        data = self._request("GET", f"/v1/messages/{provider_message_id}")
        if data.get("status") not in _REPORTABLE_STATUSES:
            return None
        try:
            return self._to_event(data, message_id_key="id", time_key="updated_at")
        except (KeyError, ValueError, TypeError) as exc:
            raise GatewayRejectedError("Unexpected status response") from exc

    def health(self) -> GatewayHealth:
        try:
            data = self._request("GET", "/health")
        except GatewayError as exc:
            return GatewayHealth(status=HealthStatus.DOWN, detail=str(exc))
        try:
            return GatewayHealth(status=HealthStatus(str(data.get("status"))))
        except ValueError:
            return GatewayHealth(status=HealthStatus.DEGRADED, detail="Unknown health status")

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> list[StatusEvent]:
        self._verify_signature(headers.get(SIGNATURE_HEADER, ""), body)
        try:
            data = json.loads(body)
            return [self._to_event(data, message_id_key="message_id", time_key="occurred_at")]
        except (KeyError, ValueError, TypeError) as exc:
            raise WebhookPayloadError(str(exc)) from exc

    def _verify_signature(self, header: str, body: bytes) -> None:
        parts = dict(part.split("=", 1) for part in header.split(",") if "=" in part)
        timestamp, signature = parts.get("t", ""), parts.get("v1", "")
        if not timestamp.isdigit() or not signature:
            raise WebhookVerificationError("Missing or malformed signature header")
        if abs(time.time() - int(timestamp)) > SIGNATURE_TOLERANCE_SECONDS:
            raise WebhookVerificationError("Signature timestamp outside the tolerance window")
        expected = hmac.new(
            self._webhook_secret, f"{timestamp}.".encode() + body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise WebhookVerificationError("Signature mismatch")

    def _to_event(
        self, data: Mapping[str, Any], *, message_id_key: str, time_key: str
    ) -> StatusEvent:
        status = DeliveryStatus(data["status"])
        error = None
        if status == DeliveryStatus.FAILED:
            error_data = data.get("error")
            if not isinstance(error_data, dict):
                error_data = {}
            error_class = ERRORS_BY_CODE.get(error_data.get("code", ""), GatewayRejectedError)
            error = error_class(str(error_data.get("message", "")))
        return StatusEvent(
            provider_message_id=str(data[message_id_key]),
            status=status,
            occurred_at=_parse_timestamp(data[time_key]),
            provider_event_id=data.get("event_id"),
            idempotency_key=data.get("idempotency_key"),
            error=error,
            raw=dict(data),
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._session.request(
                method, f"{self._base_url}{path}", timeout=self._timeout, **kwargs
            )
        except requests.RequestException as exc:
            raise GatewayUnavailableError(f"{type(exc).__name__}: {exc}") from exc

        if response.ok:
            data = _json_object(response)
            if data is None:
                raise GatewayRejectedError("Response is not a JSON object")
            return data
        raise self._error_for(response)

    @staticmethod
    def _error_for(response: requests.Response) -> GatewayError:
        body = _json_object(response) or {}
        error = body.get("error")
        if not isinstance(error, dict):
            error = {}
        detail = f"HTTP {response.status_code}: {error.get('message', response.reason)}"

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "")
            return RateLimitedError(
                detail, retry_after=float(retry_after) if retry_after.isdigit() else None
            )
        if response.status_code >= 500:
            return GatewayUnavailableError(detail)
        if error.get("code") == InvalidRecipientError.code or response.status_code == 422:
            return InvalidRecipientError(detail)
        return ERRORS_BY_CODE.get(error.get("code", ""), GatewayRejectedError)(detail)


def _json_object(response: requests.Response) -> dict[str, Any] | None:
    """The body as a JSON object, or None for any other body (lists, strings, HTML)."""
    try:
        data = response.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _parse_timestamp(value: str) -> datetime:
    """ISO 8601; a timestamp without an offset is taken as UTC."""
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
