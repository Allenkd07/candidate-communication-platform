from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

import pytest

from candidate_comms.integrations.messaging import registry
from candidate_comms.integrations.messaging.base import (
    GatewayHealth,
    HealthStatus,
    MessagingGateway,
    SendRequest,
    SendResult,
    StatusEvent,
)
from candidate_comms.integrations.messaging.exceptions import GatewayError
from candidate_comms.realtime import publisher


@dataclass
class PublishedEvents:
    messages: list[tuple[str, str]] = field(default_factory=list)

    def publish(self, channel: str, message: str) -> None:
        self.messages.append((channel, message))


@pytest.fixture(autouse=True)
def published_events(monkeypatch: pytest.MonkeyPatch) -> PublishedEvents:
    """Captures realtime publishes instead of sending them to Redis."""
    events = PublishedEvents()
    monkeypatch.setattr(publisher, "_client", lambda: events)
    return events


class FakeGateway(MessagingGateway):
    """In-memory gateway: `send_outcomes` are consumed one per send (an error is raised)."""

    name = "simulator"

    def __init__(self) -> None:
        self.sent: list[SendRequest] = []
        self.send_outcomes: list[GatewayError | None] = []
        self.statuses: dict[str, StatusEvent | None] = {}

    def send(self, request: SendRequest) -> SendResult:
        self.sent.append(request)
        outcome = self.send_outcomes.pop(0) if self.send_outcomes else None
        if outcome is not None:
            raise outcome
        return SendResult(provider_message_id=f"prov-{request.idempotency_key}")

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> list[StatusEvent]:
        raise NotImplementedError

    def fetch_status(self, provider_message_id: str) -> StatusEvent | None:
        return self.statuses.get(provider_message_id)

    def health(self) -> GatewayHealth:
        return GatewayHealth(status=HealthStatus.OPERATIONAL)


@pytest.fixture(autouse=True)
def _clear_gateway_cache() -> Iterator[None]:
    registry.get_gateway.cache_clear()
    yield
    registry.get_gateway.cache_clear()


@pytest.fixture
def fake_gateway(monkeypatch: pytest.MonkeyPatch) -> FakeGateway:
    gateway = FakeGateway()
    factories: dict[str, Any] = {**registry.GATEWAY_FACTORIES, FakeGateway.name: lambda: gateway}
    monkeypatch.setattr(registry, "GATEWAY_FACTORIES", factories)
    return gateway
