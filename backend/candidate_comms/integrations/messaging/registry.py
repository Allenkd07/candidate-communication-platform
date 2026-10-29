from collections.abc import Callable
from functools import cache

from django.conf import settings

from .base import MessagingGateway
from .simulator.gateway import SimulatorGateway


class UnknownGatewayError(LookupError):
    pass


def _build_simulator() -> MessagingGateway:
    return SimulatorGateway(
        base_url=settings.SIMULATOR_API_URL,
        api_key=settings.SIMULATOR_API_KEY,
        webhook_secret=settings.SIMULATOR_WEBHOOK_SECRET,
        timeout=settings.SIMULATOR_TIMEOUT_SECONDS,
    )


GATEWAY_FACTORIES: dict[str, Callable[[], MessagingGateway]] = {
    SimulatorGateway.name: _build_simulator,
}


@cache
def get_gateway(name: str) -> MessagingGateway:
    try:
        factory = GATEWAY_FACTORIES[name]
    except KeyError:
        raise UnknownGatewayError(name) from None
    return factory()


def default_gateway_name(channel: str) -> str:
    return str(settings.MESSAGING_DEFAULT_GATEWAYS[channel])
