import json

import pytest
import redis

from candidate_comms.conftest import PublishedEvents
from candidate_comms.realtime import publisher
from candidate_comms.realtime.views import format_sse


def test_format_sse_uses_named_events() -> None:
    assert format_sse("message.status", '{"a": 1}') == 'event: message.status\ndata: {"a": 1}\n\n'


def test_publish_sends_a_typed_envelope(published_events: PublishedEvents) -> None:
    publisher.publish("message.status", {"status": "sent"})

    [(_, raw)] = published_events.messages
    assert json.loads(raw) == {"type": "message.status", "data": {"status": "sent"}}


def test_publish_failures_are_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenRedis:
        def publish(self, channel: str, message: str) -> None:
            raise redis.ConnectionError("down")

    monkeypatch.setattr(publisher, "_client", BrokenRedis)

    publisher.publish("message.status", {"status": "sent"})
