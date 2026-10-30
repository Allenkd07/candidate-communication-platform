from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from django.core.cache import cache
from django.db.models import BooleanField, Case, Count, Q, QuerySet, Value, When
from django.shortcuts import get_object_or_404
from django.utils import timezone

from candidate_comms.candidates.selectors import candidate_get
from candidate_comms.integrations.messaging import registry
from candidate_comms.integrations.messaging.base import (
    GatewayHealth,
    HealthStatus,
    MessagingGateway,
)

from .models import Message, MessageBatch, MessageStatus, MessageTemplate

# Failed messages a recruiter may send again.
RETRYABLE = Q(
    status=MessageStatus.FAILED,
    is_retryable=True,
    retried_by__isnull=True,
    candidate__is_deleted=False,
)


def with_can_retry(queryset: QuerySet[Message]) -> QuerySet[Message]:
    return queryset.annotate(
        can_retry=Case(
            When(RETRYABLE, then=Value(True)), default=Value(False), output_field=BooleanField()
        )
    )


def candidate_message_history(*, candidate_id: UUID) -> QuerySet[Message]:
    """A candidate's messages (retries included), newest first. 404 for an unknown candidate."""
    candidate = candidate_get(candidate_id=candidate_id)
    return with_can_retry(Message.objects.filter(candidate=candidate)).order_by("-created_at")


@dataclass(frozen=True)
class BatchSummary:
    batch: MessageBatch
    messages: list[Message]
    counts: dict[str, int]

    @property
    def total(self) -> int:
        return len(self.messages)


def batch_summary(*, batch_id: UUID) -> BatchSummary:
    """A batch with every recipient's latest attempt and a per-status count.

    A message that was retried is replaced by its retry, so each candidate appears once.
    """
    batch = get_object_or_404(MessageBatch, id=batch_id)
    latest = batch.messages.filter(retried_by__isnull=True).select_related("candidate")
    messages = list(with_can_retry(latest).order_by("candidate__full_name", "id"))
    tally = Counter(message.status for message in messages)
    counts = {status.value: tally.get(status.value, 0) for status in MessageStatus}
    return BatchSummary(batch=batch, messages=messages, counts=counts)


HEALTH_WINDOW = timedelta(hours=24)
HEALTH_CACHE_SECONDS = 15
_REACHED_PROVIDER = Q(sent_at__isnull=False) | Q(
    status__in=[MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.READ]
)
_DELIVERED = Q(delivered_at__isnull=False) | Q(
    status__in=[MessageStatus.DELIVERED, MessageStatus.READ]
)
_SEVERITY = [HealthStatus.OPERATIONAL, HealthStatus.DEGRADED, HealthStatus.DOWN]


@dataclass(frozen=True)
class ProviderHealth:
    name: str
    label: str
    channel: str
    status: HealthStatus
    detail: str
    sent: int
    delivered: int
    failed: int


@dataclass(frozen=True)
class ServiceHealth:
    status: HealthStatus
    window_hours: int
    providers: list[ProviderHealth]


def service_health() -> ServiceHealth:
    """Each provider's reachability plus its message counts over the last 24 hours.

    The service is as healthy as its least healthy provider.
    """
    since = timezone.now() - HEALTH_WINDOW
    rows = (
        Message.objects.filter(created_at__gte=since)
        .values("gateway")
        .annotate(
            sent=Count("id", filter=_REACHED_PROVIDER),
            delivered=Count("id", filter=_DELIVERED),
            failed=Count("id", filter=Q(status=MessageStatus.FAILED)),
        )
    )
    counts = {row["gateway"]: (row["sent"], row["delivered"], row["failed"]) for row in rows}
    gateways = {name: registry.get_gateway(name) for name in registry.GATEWAY_FACTORIES}
    with ThreadPoolExecutor(max_workers=max(len(gateways), 1)) as pool:
        checks = {name: pool.submit(_cached_health, name, gw) for name, gw in gateways.items()}
    providers = []
    for name, gateway in gateways.items():
        sent, delivered, failed = counts.get(name, (0, 0, 0))
        health = checks[name].result()
        providers.append(
            ProviderHealth(
                name=name,
                label=gateway.label,
                channel=gateway.channel,
                status=health.status,
                detail=health.detail,
                sent=sent,
                delivered=delivered,
                failed=failed,
            )
        )
    worst = max((p.status for p in providers), key=_SEVERITY.index, default=HealthStatus.DOWN)
    return ServiceHealth(
        status=worst, window_hours=int(HEALTH_WINDOW.total_seconds() // 3600), providers=providers
    )


def _cached_health(name: str, gateway: MessagingGateway) -> GatewayHealth:
    key = f"gateway-health:{name}"
    health = cache.get(key)
    if not isinstance(health, GatewayHealth):
        health = gateway.health()
        cache.set(key, health, HEALTH_CACHE_SECONDS)
    return health


def template_list() -> QuerySet[MessageTemplate]:
    return MessageTemplate.objects.order_by("name")


def template_get(*, template_id: UUID) -> MessageTemplate:
    return get_object_or_404(MessageTemplate, id=template_id)
