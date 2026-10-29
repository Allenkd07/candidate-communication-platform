from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .exceptions import GatewayError


class DeliveryStatus(StrEnum):
    """Statuses a gateway can report after accepting a message."""

    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class HealthStatus(StrEnum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass(frozen=True)
class SendRequest:
    recipient: str
    body: str
    idempotency_key: str
    callback_url: str


@dataclass(frozen=True)
class SendResult:
    provider_message_id: str


@dataclass(frozen=True)
class StatusEvent:
    provider_message_id: str
    status: DeliveryStatus
    occurred_at: datetime
    # Unique per gateway for webhook events; None for polled statuses.
    provider_event_id: str | None = None
    # The idempotency key sent with the message, when the gateway echoes it back.
    idempotency_key: str | None = None
    error: GatewayError | None = None
    raw: Mapping[str, object] | None = None


@dataclass(frozen=True)
class GatewayHealth:
    status: HealthStatus
    detail: str = ""


class MessagingGateway(ABC):
    """A messaging vendor. Implementations raise only GatewayError subclasses."""

    name: str

    @abstractmethod
    def send(self, request: SendRequest) -> SendResult:
        """Submit a message. Repeating a call with the same idempotency key is safe."""

    @abstractmethod
    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> list[StatusEvent]:
        """Verify a webhook and normalize it.

        Raises WebhookVerificationError or WebhookPayloadError.
        """

    @abstractmethod
    def fetch_status(self, provider_message_id: str) -> StatusEvent | None:
        """Current status of a message, or None while it has no reportable status."""

    @abstractmethod
    def health(self) -> GatewayHealth: ...
