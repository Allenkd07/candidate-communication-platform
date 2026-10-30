from typing import Any

from rest_framework import serializers

from candidate_comms.core.pagination import paginated_serializer
from candidate_comms.integrations.messaging.base import HealthStatus

from .models import MESSAGE_BODY_MAX_LENGTH, TEMPLATE_NAME_MAX_LENGTH, Channel, MessageStatus
from .services.dispatch import MAX_RECIPIENTS


class MessageSendInputSerializer(serializers.Serializer[Any]):
    candidate_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=MAX_RECIPIENTS
    )
    body = serializers.CharField(max_length=MESSAGE_BODY_MAX_LENGTH)
    channel = serializers.ChoiceField(choices=Channel.choices, default=Channel.SMS)
    scheduled_at = serializers.DateTimeField(
        required=False,
        default=None,
        help_text="Send later: between 1 minute and 30 days from now. Omit to send now.",
    )
    idempotency_key = serializers.UUIDField(
        required=False,
        default=None,
        help_text=(
            "A new UUID per message. Resending with the same key (for example after a lost "
            "response) returns the original batch instead of messaging everyone again."
        ),
    )


class MessageOutputSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    batch_id = serializers.UUIDField()
    candidate_id = serializers.UUIDField()
    channel = serializers.ChoiceField(choices=Channel.choices)
    recipient = serializers.CharField()
    body = serializers.CharField()
    status = serializers.ChoiceField(choices=MessageStatus.choices)
    status_changed_at = serializers.DateTimeField()
    scheduled_for = serializers.DateTimeField(
        allow_null=True, help_text="When a scheduled message will be sent"
    )
    attempt_count = serializers.IntegerField()
    failure_code = serializers.CharField()
    failure_reason = serializers.CharField()
    is_retryable = serializers.BooleanField()
    can_retry = serializers.BooleanField(
        help_text="The recruiter can send this failed message again"
    )
    retry_of_id = serializers.UUIDField(
        allow_null=True, help_text="The failed message this one retries"
    )
    created_at = serializers.DateTimeField()
    sent_at = serializers.DateTimeField(allow_null=True)
    delivered_at = serializers.DateTimeField(allow_null=True)
    read_at = serializers.DateTimeField(allow_null=True)
    failed_at = serializers.DateTimeField(allow_null=True)


MessagePageSerializer = paginated_serializer(MessageOutputSerializer, name="MessagePage")


class TemplateInputSerializer(serializers.Serializer[Any]):
    name = serializers.CharField(max_length=TEMPLATE_NAME_MAX_LENGTH)
    body = serializers.CharField(
        max_length=MESSAGE_BODY_MAX_LENGTH,
        help_text="May use {{first_name}} and {{full_name}}",
    )


class TemplateOutputSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    name = serializers.CharField()
    body = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ProviderHealthSerializer(serializers.Serializer[Any]):
    name = serializers.CharField()
    display_name = serializers.CharField(source="label", help_text="Shown to recruiters")
    channel = serializers.ChoiceField(choices=Channel.choices, help_text="The channel it delivers")
    status = serializers.ChoiceField(choices=[s.value for s in HealthStatus])
    detail = serializers.CharField(help_text="Why the provider is not operational, if known")
    sent = serializers.IntegerField(help_text="Messages that reached the provider")
    delivered = serializers.IntegerField()
    failed = serializers.IntegerField()


class ServiceHealthSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(
        choices=[s.value for s in HealthStatus], help_text="The least healthy provider's status"
    )
    window_hours = serializers.IntegerField(help_text="Period the message counts cover")
    providers = ProviderHealthSerializer(many=True)


class BatchCandidateSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    code = serializers.CharField()
    full_name = serializers.CharField()


class BatchMessageSerializer(MessageOutputSerializer):
    candidate = BatchCandidateSerializer()


class BatchStatusCountsSerializer(serializers.Serializer[Any]):
    scheduled = serializers.IntegerField()
    queued = serializers.IntegerField()
    sent = serializers.IntegerField()
    delivered = serializers.IntegerField()
    read = serializers.IntegerField()
    failed = serializers.IntegerField()


class BatchOutputSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField(source="batch.id")
    body = serializers.CharField(source="batch.body")
    channel = serializers.ChoiceField(source="batch.channel", choices=Channel.choices)
    gateway = serializers.CharField(source="batch.gateway")
    created_at = serializers.DateTimeField(source="batch.created_at")
    total = serializers.IntegerField()
    counts = BatchStatusCountsSerializer()
    messages = BatchMessageSerializer(many=True)
