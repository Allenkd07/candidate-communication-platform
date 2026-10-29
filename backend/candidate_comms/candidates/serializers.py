from typing import Any

from rest_framework import serializers

from candidate_comms.communications.models import MessageStatus
from candidate_comms.core.pagination import paginated_serializer

from .services import MAX_BULK_DELETE
from .validators import NAME_MAX_LENGTH, normalize_email, normalize_full_name, normalize_phone


class CandidateListFilterSerializer(serializers.Serializer[Any]):
    search = serializers.CharField(required=False, allow_blank=True, default="", max_length=100)


class CandidateCreateInputSerializer(serializers.Serializer[Any]):
    full_name = serializers.CharField(max_length=NAME_MAX_LENGTH * 2)
    phone = serializers.CharField(max_length=32)
    email = serializers.EmailField()

    def validate_full_name(self, value: str) -> str:
        return normalize_full_name(value)

    def validate_phone(self, value: str) -> str:
        return normalize_phone(value)

    def validate_email(self, value: str) -> str:
        return normalize_email(value)


class CandidateOutputSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    code = serializers.CharField()
    full_name = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField()
    created_at = serializers.DateTimeField()


class CandidateListOutputSerializer(CandidateOutputSerializer):
    last_message_at = serializers.DateTimeField(allow_null=True)
    last_message_status = serializers.ChoiceField(choices=MessageStatus.choices, allow_null=True)
    last_message_body = serializers.CharField(allow_null=True)


CandidatePageSerializer = paginated_serializer(CandidateListOutputSerializer, name="CandidatePage")


class CandidateBulkDeleteInputSerializer(serializers.Serializer[Any]):
    candidate_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=MAX_BULK_DELETE
    )


class CandidateBulkDeleteOutputSerializer(serializers.Serializer[Any]):
    deleted = serializers.IntegerField()
