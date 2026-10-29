from typing import Any

from rest_framework import serializers

from candidate_comms.core.pagination import paginated_serializer

from .models import MESSAGE_BODY_MAX_LENGTH, Channel, MessageStatus
from .services.dispatch import MAX_RECIPIENTS


class MessageSendInputSerializer(serializers.Serializer[Any]):
    candidate_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=MAX_RECIPIENTS
    )
    body = serializers.CharField(max_length=MESSAGE_BODY_MAX_LENGTH)
    channel = serializers.ChoiceField(choices=Channel.choices, default=Channel.SMS)


class MessageOutputSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    batch_id = serializers.UUIDField()
    candidate_id = serializers.UUIDField()
    channel = serializers.ChoiceField(choices=Channel.choices)
    recipient = serializers.CharField()
    body = serializers.CharField()
    status = serializers.ChoiceField(choices=MessageStatus.choices)
    status_changed_at = serializers.DateTimeField()
    attempt_count = serializers.IntegerField()
    failure_code = serializers.CharField()
    failure_reason = serializers.CharField()
    is_retryable = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    sent_at = serializers.DateTimeField(allow_null=True)
    delivered_at = serializers.DateTimeField(allow_null=True)
    read_at = serializers.DateTimeField(allow_null=True)
    failed_at = serializers.DateTimeField(allow_null=True)


MessagePageSerializer = paginated_serializer(MessageOutputSerializer, name="MessagePage")


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
