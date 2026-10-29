"""Publishes domain events to Redis pub/sub; the SSE endpoint fans them out to browsers.

Publishing is best-effort: a Redis failure is logged and never fails the database change
that triggered it. Clients recover missed events by refetching.
"""

import json
import logging
from functools import cache
from typing import Any

import redis
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)


@cache
def _client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2, socket_connect_timeout=2)


def publish(event_type: str, data: dict[str, Any]) -> None:
    message = json.dumps({"type": event_type, "data": data}, cls=DjangoJSONEncoder)
    try:
        _client().publish(settings.REALTIME_CHANNEL, message)
    except redis.RedisError:
        logger.warning("Realtime publish failed for %s", event_type, exc_info=True)
