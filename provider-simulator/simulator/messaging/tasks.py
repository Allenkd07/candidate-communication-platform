import logging

from celery import Task, shared_task
from django.conf import settings

from .models import MessageStatus
from .services import message_advance
from .webhooks import webhook_deliver, webhook_retry_delay_seconds

logger = logging.getLogger(__name__)


@shared_task
def advance_message(message_id: str, from_status: str) -> None:
    message_advance(message_id=message_id, from_status=MessageStatus(from_status))


@shared_task(bind=True, max_retries=settings.WEBHOOK_MAX_RETRIES)
def deliver_webhook(self: Task, event_id: str) -> None:
    result = webhook_deliver(event_id=event_id)
    if result.delivered or not result.retryable:
        return
    if self.request.retries >= self.max_retries:
        # The platform's reconciliation recovers the status by polling GET /v1/messages/{id}.
        logger.warning("Webhook %s dropped after %s retries", event_id, self.max_retries)
        return
    raise self.retry(countdown=webhook_retry_delay_seconds(retries=self.request.retries))
