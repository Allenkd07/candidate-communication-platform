from dataclasses import dataclass, field
from typing import Any

import pytest
from django.conf import settings
from django.test import Client

from simulator.messaging import services

SEND_URL = "/v1/messages"
CALLBACK_URL = "http://api:8000/api/v1/webhooks/simulator/"


@pytest.fixture
def api_client() -> Client:
    return Client(headers={"Authorization": f"Bearer {settings.SIMULATOR_API_KEY}"})


@dataclass
class Scheduled:
    """Lifecycle steps and webhook deliveries queued by the code under test."""

    steps: list[str] = field(default_factory=list)
    webhooks: list[str] = field(default_factory=list)


@pytest.fixture
def scheduled(monkeypatch: pytest.MonkeyPatch) -> Scheduled:
    queued = Scheduled()
    monkeypatch.setattr(
        services,
        "lifecycle_schedule",
        lambda message_id, from_status: queued.steps.append(message_id),
    )
    monkeypatch.setattr(services, "webhook_schedule", queued.webhooks.append)
    return queued


def send_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "to": "+919845012345",
        "body": "Interview tomorrow at 10?",
        "idempotency_key": "key-1",
        "callback_url": CALLBACK_URL,
    }
    payload.update(overrides)
    return payload
