import asyncio
import json

import pytest
import redis
from django.test import RequestFactory

from candidate_comms.conftest import PublishedEvents
from candidate_comms.realtime import publisher
from candidate_comms.realtime.views import event_stream_view, format_sse


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


def test_stream_forbids_proxy_compression() -> None:
    # A compressing proxy buffers the stream, so events would never reach the browser.
    response = asyncio.run(event_stream_view(RequestFactory().get("/api/v1/events/")))

    assert response["Content-Type"] == "text/event-stream"
    assert "no-transform" in response["Cache-Control"]
