import random
from enum import StrEnum

from django.db import transaction

from simulator.core.errors import ErrorCode, ProviderError

from .models import FaultConfig

_SINGLETON_ID = 1


class HealthStatus(StrEnum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"


def faults_get() -> FaultConfig:
    config, _ = FaultConfig.objects.get_or_create(id=_SINGLETON_ID)
    return config


def faults_update(
    *, outage: bool | None = None, failure_rate: float | None = None, latency_ms: int | None = None
) -> FaultConfig:
    """Change only the given faults; the others keep their current value."""
    changes = {
        name: value
        for name, value in (
            ("outage", outage),
            ("failure_rate", failure_rate),
            ("latency_ms", latency_ms),
        )
        if value is not None
    }
    with transaction.atomic():
        faults_get()
        # Locked so concurrent partial updates never overwrite each other's fields.
        config = FaultConfig.objects.select_for_update().get(id=_SINGLETON_ID)
        for name, value in changes.items():
            setattr(config, name, value)
        config.save(update_fields=[*changes, "updated_at"])
    return config


def faults_latency_seconds() -> float:
    return faults_get().latency_ms / 1000


def faults_apply() -> None:
    """Fail one API call when an outage or random failures are injected.

    Latency is applied separately by LatencyMiddleware, so it never blocks other requests.
    """
    config = faults_get()
    if config.outage:
        raise ProviderError(
            "The provider is down.", code=ErrorCode.GATEWAY_UNAVAILABLE, status_code=503
        )
    if config.failure_rate and random.random() < config.failure_rate:
        raise ProviderError(
            "Temporary provider failure.", code=ErrorCode.GATEWAY_UNAVAILABLE, status_code=503
        )


def health_status() -> HealthStatus:
    config = faults_get()
    if config.outage:
        return HealthStatus.DOWN
    if config.failure_rate or config.latency_ms:
        return HealthStatus.DEGRADED
    return HealthStatus.OPERATIONAL
