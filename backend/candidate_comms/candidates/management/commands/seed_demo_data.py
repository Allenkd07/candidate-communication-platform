"""Demo data: everyday candidates with past message history, plus one candidate per
provider-simulator test number so every delivery outcome can be demonstrated."""

from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.utils import timezone

from candidate_comms.candidates.models import Candidate
from candidate_comms.candidates.services import candidate_create
from candidate_comms.communications.models import (
    Channel,
    EventSource,
    Message,
    MessageBatch,
    MessageEvent,
    MessageStatus,
    MessageTemplate,
)
from candidate_comms.communications.services.delivery import Failure, message_apply_status
from candidate_comms.communications.services.templates import template_create
from candidate_comms.integrations.messaging.exceptions import DeliveryFailedError
from candidate_comms.integrations.messaging.registry import default_gateway_name

# (full name, phone, email, final status of a past message or None for no history)
CANDIDATES: list[tuple[str, str, str, MessageStatus | None]] = [
    ("Taylor Swift", "+919845012345", "taylor.swift@example.com", MessageStatus.READ),
    ("Aarav Sharma", "+917012345678", "aarav.sharma@example.com", MessageStatus.DELIVERED),
    ("Priya Nair", "+918123456789", "priya.nair@example.com", MessageStatus.SENT),
    ("Rohan Mehta", "+919900112233", "rohan.mehta@example.com", MessageStatus.FAILED),
    ("Ananya Iyer", "+916300123456", "ananya.iyer@example.com", MessageStatus.READ),
    ("Vikram Rao", "+919011223344", "vikram.rao@example.com", None),
    ("Meera Kapoor", "+918800765432", "meera.kapoor@example.com", None),
]

# The simulator decides the outcome from the last four digits (see provider-simulator).
TEST_NUMBER_CANDIDATES: list[tuple[str, str, str]] = [
    ("Test Invalid Number", "+919876500000", "test.invalid@example.com"),
    ("Test Delivery Fails", "+919876511111", "test.delivery-fails@example.com"),
    ("Test Flaky Provider", "+919876522222", "test.flaky@example.com"),
    ("Test Rate Limited", "+919876533333", "test.rate-limited@example.com"),
    ("Test Never Read", "+919876544444", "test.never-read@example.com"),
    # Resend's test inboxes for the email channel.
    ("Test Email Delivered", "+919876566661", "delivered@resend.dev"),
    ("Test Email Bounced", "+919876566662", "bounced@resend.dev"),
]

TEMPLATES: list[tuple[str, str]] = [
    (
        "Interview invite",
        "Hi {{first_name}}, thanks for applying. Are you free for a 30-minute call this week? "
        "Reply with a time that suits you.",
    ),
    (
        "Interview reminder",
        "Hi {{first_name}}, a reminder that your interview is tomorrow. "
        "Please join a few minutes early.",
    ),
    (
        "Documents needed",
        "Hello {{full_name}}, please share your updated CV and ID proof so we can move "
        "your application forward.",
    ),
]

HISTORY_BODY = "Hi {first_name}, thanks for applying. Are you free for a call this week?"
_PATH = {
    MessageStatus.SENT: (MessageStatus.SENT,),
    MessageStatus.DELIVERED: (MessageStatus.SENT, MessageStatus.DELIVERED),
    MessageStatus.READ: (MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.READ),
    MessageStatus.FAILED: (MessageStatus.SENT, MessageStatus.FAILED),
}


class Command(BaseCommand):
    help = "Create demo candidates (idempotent). --reset deletes every candidate first."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--reset", action="store_true", help="Delete all candidates and messages first"
        )

    def handle(self, *args: Any, reset: bool, **options: Any) -> None:
        if reset:
            # A real delete, including soft-deleted candidates, so the demo starts from empty.
            deleted, _ = Candidate.all_objects.all().delete()
            self.stdout.write(f"Deleted {deleted} rows")

        created = 0
        for days_ago, (full_name, phone, email, final_status) in enumerate(CANDIDATES, start=1):
            if Candidate.objects.filter(phone=phone).exists():
                continue
            candidate = candidate_create(full_name=full_name, phone=phone, email=email)
            created += 1
            if final_status is not None:
                _seed_history(candidate, final_status, days_ago=days_ago)

        for full_name, phone, email in TEST_NUMBER_CANDIDATES:
            if not Candidate.objects.filter(phone=phone).exists():
                candidate_create(full_name=full_name, phone=phone, email=email)
                created += 1

        templates = 0
        for name, body in TEMPLATES:
            if not MessageTemplate.objects.filter(name__iexact=name).exists():
                template_create(name=name, body=body)
                templates += 1

        self.stdout.write(
            self.style.SUCCESS(f"Created {created} candidates, {templates} templates")
        )


def _seed_history(candidate: Candidate, final_status: MessageStatus, *, days_ago: int) -> None:
    """A past message replayed through the state machine, so its events match a real send."""
    sent_at = timezone.now() - timedelta(days=days_ago)
    body = HISTORY_BODY.format(first_name=candidate.full_name.split()[0])
    gateway = default_gateway_name(Channel.SMS)

    with transaction.atomic():
        batch = MessageBatch.objects.create(body=body, channel=Channel.SMS, gateway=gateway)
        message = Message.objects.create(
            batch=batch,
            candidate=candidate,
            channel=Channel.SMS,
            gateway=gateway,
            recipient=candidate.phone,
            body=body,
            status=MessageStatus.QUEUED,
            status_changed_at=sent_at,
            attempt_count=1,
        )
        # Backdate creation so the candidate table shows the historical date.
        Message.objects.filter(id=message.id).update(created_at=sent_at)
        MessageEvent.objects.create(
            message=message,
            source=EventSource.PLATFORM,
            status=MessageStatus.QUEUED,
            applied=True,
            occurred_at=sent_at,
        )
        for step, status in enumerate(_PATH[final_status]):
            failure = (
                Failure.from_gateway_error(DeliveryFailedError())
                if status == MessageStatus.FAILED
                else None
            )
            message_apply_status(
                message_id=message.id,
                status=status,
                source=EventSource.PLATFORM,
                occurred_at=sent_at + timedelta(minutes=step),
                failure=failure,
            )
