from collections.abc import Callable
from functools import cache

from django.conf import settings

from .base import MessagingGateway
from .resend.gateway import ResendGateway
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


def _build_resend() -> MessagingGateway:
    return ResendGateway(
        base_url=settings.RESEND_API_URL,
        api_key=settings.RESEND_API_KEY,
        sender=settings.RESEND_FROM,
        subject=settings.RESEND_SUBJECT,
        webhook_secret=settings.RESEND_WEBHOOK_SECRET,
        timeout=settings.RESEND_TIMEOUT_SECONDS,
    )


GATEWAY_FACTORIES: dict[str, Callable[[], MessagingGateway]] = {
    SimulatorGateway.name: _build_simulator,
    **({ResendGateway.name: _build_resend} if settings.RESEND_API_KEY else {}),
}


@cache
def get_gateway(name: str) -> MessagingGateway:
    try:
        factory = GATEWAY_FACTORIES[name]
    except KeyError:
        raise UnknownGatewayError(name) from None
    return factory()


def default_gateway_name(channel: str) -> str:
    """Raises UnknownGatewayError for a channel with no configured gateway."""
    try:
        return str(settings.MESSAGING_DEFAULT_GATEWAYS[channel])
    except KeyError:
        raise UnknownGatewayError(channel) from None
