import asyncio
from collections.abc import Awaitable, Callable

from asgiref.sync import markcoroutinefunction, sync_to_async
from django.http import HttpRequest, HttpResponseBase

from .services import faults_latency_seconds

# Only the provider API is slowed down; health and fault control stay responsive.
_DELAYED_PREFIX = "/v1/"


class LatencyMiddleware:
    """Delays provider API calls by the injected latency.

    The delay is an asyncio sleep, so it waits without occupying the single thread that
    Django uses for sync views under ASGI; other requests keep being served meanwhile.
    """

    async_capable = True
    sync_capable = False

    def __init__(self, get_response: Callable[[HttpRequest], Awaitable[HttpResponseBase]]) -> None:
        self.get_response = get_response
        markcoroutinefunction(self)

    async def __call__(self, request: HttpRequest) -> HttpResponseBase:
        if request.path.startswith(_DELAYED_PREFIX):
            delay = await sync_to_async(faults_latency_seconds)()
            if delay:
                await asyncio.sleep(delay)
        return await self.get_response(request)
