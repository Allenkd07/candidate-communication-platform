from uuid import UUID

from celery import Task, shared_task
from django.conf import settings

from .services.delivery import Failure
from .services.dispatch import message_fail, message_send_attempt, retry_delay_seconds
from .services.reconciliation import stale_messages_reconcile
from .services.scheduling import scheduled_messages_release


@shared_task(bind=True, max_retries=settings.MESSAGE_SEND_MAX_RETRIES)
def send_message(self: Task, message_id: str) -> None:
    result = message_send_attempt(message_id=UUID(message_id))
    error = result.retry_error
    if error is None:
        return
    if self.request.retries >= self.max_retries:
        failure = Failure.from_gateway_error(error, retries_exhausted=True)
        message_fail(message_id=UUID(message_id), failure=failure)
        return
    countdown = retry_delay_seconds(retries=self.request.retries, error=error)
    raise self.retry(exc=error, countdown=countdown)


@shared_task
def reconcile_stale_messages() -> dict[str, int]:
    result = stale_messages_reconcile()
    return {
        "checked": result.checked,
        "updated": result.updated,
        "requeued": result.requeued,
        "abandoned": result.abandoned,
    }


@shared_task
def release_scheduled_messages() -> dict[str, int]:
    result = scheduled_messages_release()
    return {"released": result.released, "cancelled": result.cancelled}
