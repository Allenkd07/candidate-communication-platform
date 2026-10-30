from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from candidate_comms.communications.models import Message, MessageStatus
from candidate_comms.conftest import FakeGateway
from candidate_comms.integrations.messaging.base import GatewayHealth, HealthStatus

from .factories import MessageFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/providers/health/"


@pytest.fixture(autouse=True)
def _fresh_cache() -> None:
    cache.clear()


def health(client: Client) -> dict[str, Any]:
    response = client.get(URL)
    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    return data


def test_counts_cover_the_last_24_hours(client: Client, fake_gateway: FakeGateway) -> None:
    now = timezone.now()
    MessageFactory.create(status=MessageStatus.QUEUED)
    MessageFactory.create(status=MessageStatus.SENT, sent_at=now)
    MessageFactory.create(status=MessageStatus.DELIVERED, sent_at=now, delivered_at=now)
    MessageFactory.create(status=MessageStatus.READ, sent_at=now, read_at=now)
    MessageFactory.create(status=MessageStatus.FAILED)
    old = MessageFactory.create(status=MessageStatus.FAILED)
    Message.objects.filter(id=old.id).update(created_at=now - timedelta(days=2))

    data = health(client)

    assert data["status"] == "operational"
    assert data["window_hours"] == 24
    [provider] = data["providers"]
    assert provider["name"] == "simulator"
    assert provider["display_name"] == "SMS"
    assert (provider["sent"], provider["delivered"], provider["failed"]) == (3, 2, 1)


def test_reports_the_provider_being_down(client: Client, fake_gateway: FakeGateway) -> None:
    fake_gateway.health_result = GatewayHealth(
        status=HealthStatus.DOWN, detail="Connection refused"
    )

    data = health(client)

    assert data["status"] == "down"
    assert data["providers"][0]["detail"] == "Connection refused"


def test_provider_check_is_cached_briefly(client: Client, fake_gateway: FakeGateway) -> None:
    health(client)
    fake_gateway.health_result = GatewayHealth(status=HealthStatus.DOWN)

    assert health(client)["status"] == "operational"
    cache.clear()
    assert health(client)["status"] == "down"
