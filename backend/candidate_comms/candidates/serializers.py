from typing import Any

from rest_framework import serializers

from candidate_comms.communications.models import MessageStatus
from candidate_comms.core.pagination import paginated_serializer

from .selectors import NO_MESSAGES, SORT_KEYS
from .services import MAX_BULK_DELETE
from .validators import NAME_MAX_LENGTH, normalize_email, normalize_full_name, normalize_phone


class CandidateListFilterSerializer(serializers.Serializer[Any]):
    search = serializers.CharField(required=False, allow_blank=True, default="", max_length=100)
    name = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=100, help_text="Name contains"
    )
    phone = serializers.RegexField(
        r"^[\d\s()+\-]*$",
        required=False,
        allow_blank=True,
        default="",
        max_length=20,
        help_text="Mobile number contains these digits",
    )
    code = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=6,
        help_text="Candidate ID contains",
    )
    status = serializers.ListField(
        child=serializers.ChoiceField(choices=[*MessageStatus.values, NO_MESSAGES]),
        required=False,
        default=list,
        help_text=f"Latest message status is any of these; `{NO_MESSAGES}` matches never messaged",
    )
    last_message_after = serializers.DateTimeField(
        required=False, default=None, help_text="Latest message sent at or after"
    )
    last_message_before = serializers.DateTimeField(
        required=False, default=None, help_text="Latest message sent before"
    )
    sort = serializers.ChoiceField(
        choices=[*SORT_KEYS, *(f"-{key}" for key in SORT_KEYS)],
        required=False,
        allow_blank=True,
        default="",
        help_text=(
            "Column to sort by, `-` prefix for descending; newest first by default. Status "
            "sorts in lifecycle order; candidates never messaged come last"
        ),
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        after, before = attrs["last_message_after"], attrs["last_message_before"]
        if after and before and after >= before:
            raise serializers.ValidationError(
                {"last_message_before": "Must be later than last_message_after."}
            )
        return attrs


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
    # Recruiter-facing reason when the latest message failed; empty otherwise.
    last_message_failure_reason = serializers.CharField(allow_null=True)


CandidatePageSerializer = paginated_serializer(CandidateListOutputSerializer, name="CandidatePage")


class CandidateBulkDeleteInputSerializer(serializers.Serializer[Any]):
    candidate_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=MAX_BULK_DELETE
    )


class CandidateBulkDeleteOutputSerializer(serializers.Serializer[Any]):
    deleted = serializers.IntegerField()
