import uuid

from django.db import models
from django.db.models.functions import Lower

from candidate_comms.candidates.models import Candidate
from candidate_comms.core.models import BaseModel

MESSAGE_BODY_MAX_LENGTH = 1000
TEMPLATE_NAME_MAX_LENGTH = 60


class Channel(models.TextChoices):
    SMS = "sms", "SMS"
    EMAIL = "email", "Email"


class MessageStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    READ = "read", "Read"
    FAILED = "failed", "Failed"


class EventSource(models.TextChoices):
    PLATFORM = "platform", "Platform"
    WEBHOOK = "webhook", "Webhook"
    RECONCILIATION = "reconciliation", "Reconciliation"


class MessageBatch(BaseModel):
    """One send action. A single send is a batch of one recipient."""

    body = models.TextField(max_length=MESSAGE_BODY_MAX_LENGTH)
    channel = models.CharField(max_length=16, choices=Channel.choices)
    gateway = models.CharField(max_length=32, help_text="Registry name of the gateway used")
    idempotency_key = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        help_text="Client-chosen key; a repeated send with the same key returns this batch",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "message batches"


class Message(BaseModel):
    """One recipient of a batch. `status` changes only through the delivery state machine."""

    batch = models.ForeignKey(MessageBatch, on_delete=models.CASCADE, related_name="messages")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="messages")
    channel = models.CharField(max_length=16, choices=Channel.choices)
    gateway = models.CharField(max_length=32)
    # Address at send time, so history stays accurate if the candidate's details change.
    recipient = models.CharField(max_length=254)
    body = models.TextField(max_length=MESSAGE_BODY_MAX_LENGTH)

    status = models.CharField(
        max_length=16, choices=MessageStatus.choices, default=MessageStatus.QUEUED
    )
    status_changed_at = models.DateTimeField()
    scheduled_for = models.DateTimeField(null=True, blank=True)
    # Sent with every attempt so the gateway never delivers the same message twice.
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    provider_message_id = models.CharField(max_length=128, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)

    failure_code = models.CharField(max_length=64, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True, help_text="Recruiter-facing")
    is_retryable = models.BooleanField(default=False, help_text="A manual retry is allowed")
    # One-to-one: a failed message is retried at most once.
    retry_of = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="retried_by"
    )

    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["gateway", "provider_message_id"],
                condition=~models.Q(provider_message_id=""),
                name="unique_provider_message_id_per_gateway",
            ),
        ]
        indexes = [
            models.Index(fields=["candidate", "-created_at"], name="message_candidate_recent"),
            models.Index(fields=["status", "status_changed_at"], name="message_status_age"),
        ]

    def __str__(self) -> str:
        return f"{self.id} → {self.recipient} [{self.status}]"


class MessageEvent(BaseModel):
    """Append-only log of every status signal, applied or not."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="events")
    source = models.CharField(max_length=16, choices=EventSource.choices)
    status = models.CharField(max_length=16, choices=MessageStatus.choices)
    # Whether the state machine accepted the signal; duplicates and stale ones are kept as False.
    applied = models.BooleanField()
    occurred_at = models.DateTimeField()
    gateway = models.CharField(max_length=32, blank=True)
    provider_event_id = models.CharField(max_length=128, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["occurred_at", "created_at"]
        constraints = [
            # Rejects a re-delivered webhook at the database level.
            models.UniqueConstraint(
                fields=["gateway", "provider_event_id"],
                condition=~models.Q(provider_event_id=""),
                name="unique_provider_event_id_per_gateway",
            ),
        ]


class MessageTemplate(BaseModel):
    """Reusable message text; its placeholders are filled in per recipient when sent."""

    name = models.CharField(max_length=TEMPLATE_NAME_MAX_LENGTH)
    body = models.TextField(max_length=MESSAGE_BODY_MAX_LENGTH)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="unique_template_name_ci"),
        ]

    def __str__(self) -> str:
        return self.name
