import logging
import random
import re
from dataclasses import dataclass
from functools import partial

from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from simulator.core.errors import ErrorCode, ProviderError

from .models import Message, MessageStatus, SendAttempt, WebhookEvent
from .scenarios import Scenario, next_status, scenario_for
from .webhooks import webhook_schedule

logger = logging.getLogger(__name__)

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")
DELIVERY_FAILED_CODE = "delivery_failed"
DELIVERY_FAILED_MESSAGE = "The carrier could not deliver the message to the handset."


@dataclass(frozen=True)
class SendOutcome:
    message: Message
    # True when the idempotency key was seen before and the original message is returned.
    replayed: bool


def message_send(*, to: str, body: str, idempotency_key: str, callback_url: str) -> SendOutcome:
    """Accept a message for delivery, or return the original one for a repeated key."""
    existing = Message.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        return _replay(existing, to=to, body=body)

    if not _E164.match(to):
        raise ProviderError(
            "'to' must be an E.164 phone number.", code=ErrorCode.INVALID_RECIPIENT, status_code=422
        )
    scenario = scenario_for(to)
    if scenario == Scenario.INVALID_RECIPIENT:
        raise ProviderError(
            "This number cannot receive messages.",
            code=ErrorCode.INVALID_RECIPIENT,
            status_code=422,
        )
    _reject_test_number_attempt(idempotency_key, scenario)

    try:
        with transaction.atomic():
            message = Message.objects.create(
                idempotency_key=idempotency_key, to=to, body=body, callback_url=callback_url
            )
            transaction.on_commit(partial(lifecycle_schedule, message.id, MessageStatus.ACCEPTED))
    except IntegrityError:
        # A concurrent request with the same key created the message first.
        return _replay(Message.objects.get(idempotency_key=idempotency_key), to=to, body=body)
    return SendOutcome(message=message, replayed=False)


def _replay(message: Message, *, to: str, body: str) -> SendOutcome:
    if (message.to, message.body) != (to, body):
        raise ProviderError(
            "This idempotency key was already used for a different message.",
            code=ErrorCode.IDEMPOTENCY_KEY_REUSED,
            status_code=409,
        )
    if message.status == MessageStatus.ACCEPTED:
        # The first request may have failed to queue the lifecycle (e.g. the broker was down)
        # after the message was saved. Steps are idempotent, so queueing it again is safe.
        lifecycle_schedule(message.id, MessageStatus.ACCEPTED)
    return SendOutcome(message=message, replayed=True)


def _reject_test_number_attempt(idempotency_key: str, scenario: Scenario) -> None:
    """Fail the first attempts for the flaky and rate-limited test numbers.

    Attempts are counted per idempotency key, so the platform's automatic retry of the same
    message is what eventually succeeds.
    """
    if scenario == Scenario.FLAKY:
        limit = settings.FLAKY_FAILED_ATTEMPTS
        error = ProviderError(
            "Temporary provider failure.", code=ErrorCode.GATEWAY_UNAVAILABLE, status_code=503
        )
    elif scenario == Scenario.RATE_LIMITED:
        limit = 1
        error = ProviderError(
            "Too many requests.",
            code=ErrorCode.RATE_LIMITED,
            status_code=429,
            headers={"Retry-After": str(settings.RATE_LIMIT_RETRY_AFTER_SECONDS)},
        )
    else:
        return

    with transaction.atomic():
        attempt, _ = SendAttempt.objects.select_for_update().get_or_create(
            idempotency_key=idempotency_key
        )
        if attempt.rejected >= limit:
            return
        attempt.rejected += 1
        attempt.save(update_fields=["rejected"])
    raise error


def lifecycle_schedule(message_id: str, from_status: MessageStatus) -> None:
    """Queue the step after `from_status` following a random, realistic delay."""
    from .tasks import advance_message

    delay = random.uniform(
        settings.LIFECYCLE_MIN_DELAY_SECONDS, settings.LIFECYCLE_MAX_DELAY_SECONDS
    )
    advance_message.apply_async(args=[message_id, from_status.value], countdown=delay)


def message_advance(*, message_id: str, from_status: MessageStatus) -> WebhookEvent | None:
    """Move the message from `from_status` to its scenario's next status and queue the webhook.

    Returns None when the message is no longer in `from_status` (a redelivered or repeated
    step) or is already final, so running a step twice never skips ahead.
    """
    with transaction.atomic():
        message = Message.objects.select_for_update().get(id=message_id)
        if message.status != from_status:
            return None
        scenario = scenario_for(message.to)
        status = next_status(from_status, scenario)
        if status is None:
            return None

        message.status = status
        if status == MessageStatus.FAILED:
            message.error_code = DELIVERY_FAILED_CODE
            message.error_message = DELIVERY_FAILED_MESSAGE
        message.save()
        event = WebhookEvent.objects.create(
            message=message, status=status, occurred_at=timezone.now()
        )
        transaction.on_commit(partial(webhook_schedule, event.id))
        if next_status(status, scenario) is not None:
            transaction.on_commit(partial(lifecycle_schedule, message.id, status))
    logger.info("Message %s is now %s", message_id, status)
    return event


def message_get(*, message_id: str) -> Message:
    return get_object_or_404(Message, id=message_id)
