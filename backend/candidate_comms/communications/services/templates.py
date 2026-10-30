"""Creating, editing and deleting message templates."""

from django.db import IntegrityError, transaction

from candidate_comms.core.exceptions import ApplicationError, ErrorCode

from ..models import MESSAGE_BODY_MAX_LENGTH, TEMPLATE_NAME_MAX_LENGTH, MessageTemplate
from ..placeholders import unknown_placeholder_error


def template_create(*, name: str, body: str) -> MessageTemplate:
    name, body = _validate(name=name, body=body)
    _raise_if_name_taken(name=name)
    try:
        with transaction.atomic():
            return MessageTemplate.objects.create(name=name, body=body)
    except IntegrityError:
        # A concurrent request saved the same name after the check above.
        _raise_if_name_taken(name=name)
        raise


def template_update(*, template: MessageTemplate, name: str, body: str) -> MessageTemplate:
    name, body = _validate(name=name, body=body)
    _raise_if_name_taken(name=name, exclude=template)
    template.name, template.body = name, body
    try:
        with transaction.atomic():
            template.save(update_fields=["name", "body", "updated_at"])
    except IntegrityError:
        _raise_if_name_taken(name=name, exclude=template)
        raise
    return template


def template_delete(*, template: MessageTemplate) -> None:
    """Sent messages keep their own text, so deleting a template changes no history."""
    template.delete()


def _validate(*, name: str, body: str) -> tuple[str, str]:
    name = " ".join(name.split())
    body = body.strip()
    fields: dict[str, list[str]] = {}
    if not name:
        fields["name"] = ["Enter a template name."]
    elif len(name) > TEMPLATE_NAME_MAX_LENGTH:
        fields["name"] = [f"Use at most {TEMPLATE_NAME_MAX_LENGTH} characters."]
    if not body:
        fields["body"] = ["Enter the template text."]
    elif len(body) > MESSAGE_BODY_MAX_LENGTH:
        fields["body"] = [f"Use at most {MESSAGE_BODY_MAX_LENGTH} characters."]
    elif placeholder_error := unknown_placeholder_error(body):
        fields["body"] = [placeholder_error]
    if fields:
        raise ApplicationError("Some fields are invalid.", fields=fields)
    return name, body


def _raise_if_name_taken(*, name: str, exclude: MessageTemplate | None = None) -> None:
    taken = MessageTemplate.objects.filter(name__iexact=name)
    if exclude is not None:
        taken = taken.exclude(id=exclude.id)
    if taken.exists():
        message = "A template with this name already exists."
        raise ApplicationError(
            message,
            code=ErrorCode.DUPLICATE_TEMPLATE,
            status_code=409,
            fields={"name": [message]},
        )
