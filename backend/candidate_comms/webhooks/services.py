from collections.abc import Mapping
from dataclasses import dataclass

from candidate_comms.communications.models import EventSource
from candidate_comms.communications.services.reconciliation import status_event_apply
from candidate_comms.communications.state_machine import Transition
from candidate_comms.core.exceptions import ApplicationError, ErrorCode
from candidate_comms.integrations.messaging.exceptions import (
    WebhookPayloadError,
    WebhookVerificationError,
)
from candidate_comms.integrations.messaging.registry import UnknownGatewayError, get_gateway


@dataclass(frozen=True)
class IngestResult:
    received: int
    applied: int
    ignored: int


def webhook_ingest(*, gateway_name: str, headers: Mapping[str, str], body: bytes) -> IngestResult:
    """Verify and apply a gateway webhook.

    Duplicate, out-of-order and unmatched events are acknowledged without changes, so the
    gateway does not keep re-delivering them.
    """
    try:
        gateway = get_gateway(gateway_name)
    except UnknownGatewayError:
        raise ApplicationError(
            "Unknown gateway.", code=ErrorCode.NOT_FOUND, status_code=404
        ) from None

    try:
        events = gateway.parse_webhook(headers, body)
    except WebhookVerificationError as exc:
        raise ApplicationError(
            "Invalid webhook signature.", code=ErrorCode.INVALID_WEBHOOK_SIGNATURE, status_code=401
        ) from exc
    except WebhookPayloadError as exc:
        raise ApplicationError(
            "Invalid webhook payload.", code=ErrorCode.INVALID_WEBHOOK_PAYLOAD, status_code=400
        ) from exc

    applied = 0
    for event in events:
        result = status_event_apply(gateway=gateway.name, event=event, source=EventSource.WEBHOOK)
        if result is not None and result.transition == Transition.APPLY:
            applied += 1
    return IngestResult(received=len(events), applied=applied, ignored=len(events) - applied)
