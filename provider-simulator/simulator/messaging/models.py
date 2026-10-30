import uuid

from django.db import models

BODY_MAX_LENGTH = 1600


def _message_id() -> str:
    return f"SM{uuid.uuid4().hex}"


def _event_id() -> str:
    return f"EV{uuid.uuid4().hex}"


class MessageStatus(models.TextChoices):
    # Received by the provider, not yet handed to the carrier.
    ACCEPTED = "accepted", "Accepted"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    READ = "read", "Read"
    FAILED = "failed", "Failed"


class Message(models.Model):
    # Provider-style ids ("SM…", "EV…") so they are never confused with the platform's UUIDs.
    id = models.CharField(primary_key=True, max_length=34, default=_message_id, editable=False)
    # A repeated send with the same key returns this message instead of creating another.
    idempotency_key = models.CharField(max_length=255, unique=True)
    to = models.CharField(max_length=16)
    body = models.TextField(max_length=BODY_MAX_LENGTH)
    callback_url = models.CharField(max_length=2048)
    status = models.CharField(
        max_length=16, choices=MessageStatus.choices, default=MessageStatus.ACCEPTED
    )
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.id} → {self.to} [{self.status}]"


class SendAttempt(models.Model):
    """Rejected send attempts per idempotency key, for test numbers that fail N times first."""

    idempotency_key = models.CharField(max_length=255, unique=True)
    rejected = models.PositiveSmallIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.idempotency_key}: {self.rejected} rejected"


class WebhookEvent(models.Model):
    """One status change, delivered to the message's callback URL as a signed webhook."""

    id = models.CharField(primary_key=True, max_length=34, default=_event_id, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=16, choices=MessageStatus.choices)
    occurred_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    delivered_at = models.DateTimeField(null=True, blank=True)
    last_response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at"]
        constraints = [
            # Each lifecycle step happens once per message; duplicate webhooks resend one event.
            models.UniqueConstraint(
                fields=["message", "status"], name="uniq_webhook_event_message_status"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.id} {self.message_id} [{self.status}]"
