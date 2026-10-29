import json
from collections.abc import AsyncIterator

import redis.asyncio as aioredis
from django.conf import settings
from django.http import HttpRequest, StreamingHttpResponse

# Tells EventSource how long to wait before reconnecting, in milliseconds.
RECONNECT_DELAY_MS = 3000


def format_sse(event_type: str, data: str) -> str:
    return f"event: {event_type}\ndata: {data}\n\n"


async def _event_stream() -> AsyncIterator[str]:
    client = aioredis.Redis.from_url(settings.REDIS_URL)
    pubsub = client.pubsub()
    await pubsub.subscribe(settings.REALTIME_CHANNEL)
    try:
        yield f"retry: {RECONNECT_DELAY_MS}\n\n"
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=settings.REALTIME_KEEPALIVE_SECONDS
            )
            if message is None:
                # Comment line: keeps proxies from closing an idle connection.
                yield ": keepalive\n\n"
                continue
            event = json.loads(message["data"])
            yield format_sse(event["type"], json.dumps(event["data"]))
    finally:
        await pubsub.aclose()  # type: ignore[no-untyped-call]
        await client.aclose()


async def event_stream_view(request: HttpRequest) -> StreamingHttpResponse:
    """Server-Sent Events stream of message status changes (`message.status`)."""
    response = StreamingHttpResponse(_event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
