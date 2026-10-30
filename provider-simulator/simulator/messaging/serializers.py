from typing import Any
from urllib.parse import urlparse

from rest_framework import serializers

from .models import BODY_MAX_LENGTH, Message, MessageStatus


class MessageSendInputSerializer(serializers.Serializer[Any]):
    # Only the length is checked here; the format check answers 422 invalid_recipient.
    to = serializers.CharField(max_length=32)
    # Stored and compared exactly as sent, so whitespace is not trimmed.
    body = serializers.CharField(max_length=BODY_MAX_LENGTH, trim_whitespace=False)
    idempotency_key = serializers.CharField(max_length=255, trim_whitespace=False)
    # Not a URLField: compose service hosts such as "api" have no dot, which URLField rejects.
    callback_url = serializers.CharField(max_length=2048)

    def validate_callback_url(self, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise serializers.ValidationError("Enter an http(s) URL.")
        return value


class MessageAcceptedSerializer(serializers.Serializer[Any]):
    id = serializers.CharField()
    status = serializers.SerializerMethodField()

    def get_status(self, message: Message) -> str:
        # The original 202 response, also for a replayed idempotency key.
        return MessageStatus.ACCEPTED.value


class MessageErrorSerializer(serializers.Serializer[Any]):
    code = serializers.CharField(source="error_code")
    message = serializers.CharField(source="error_message")


class MessageOutputSerializer(serializers.Serializer[Any]):
    id = serializers.CharField()
    to = serializers.CharField()
    status = serializers.ChoiceField(choices=MessageStatus.choices)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    error = serializers.SerializerMethodField()

    def get_error(self, message: Message) -> dict[str, Any] | None:
        if not message.error_code:
            return None
        return dict(MessageErrorSerializer(message).data)
