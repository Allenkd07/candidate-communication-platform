import secrets
import string
from collections.abc import Iterable
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from candidate_comms.core.exceptions import ApplicationError, ErrorCode

from .models import CANDIDATE_CODE_LENGTH, Candidate
from .validators import normalize_email, normalize_full_name, normalize_phone

MAX_BULK_DELETE = 500
_CREATE_ATTEMPTS = 3
_CODE_ALPHABET = string.ascii_uppercase + string.digits
_DUPLICATE_MESSAGES = {
    "phone": "A candidate with this mobile number already exists.",
    "email": "A candidate with this email already exists.",
}


def _generate_code() -> str:
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(CANDIDATE_CODE_LENGTH))
        if not Candidate.all_objects.filter(code=code).exists():
            return code


def _raise_if_duplicate(*, phone: str, email: str) -> None:
    taken = (
        Candidate.objects.filter(phone=phone).exists(),
        Candidate.objects.filter(email=email).exists(),
    )
    fields = {
        field: [_DUPLICATE_MESSAGES[field]]
        for field, is_taken in zip(("phone", "email"), taken, strict=True)
        if is_taken
    }
    if fields:
        message = (
            next(iter(fields.values()))[0]
            if len(fields) == 1
            else "A candidate with this mobile number and email already exists."
        )
        raise ApplicationError(
            message, code=ErrorCode.DUPLICATE_CANDIDATE, status_code=409, fields=fields
        )


def candidate_create(*, full_name: str, phone: str, email: str) -> Candidate:
    full_name = normalize_full_name(full_name)
    phone = normalize_phone(phone)
    email = normalize_email(email)
    _raise_if_duplicate(phone=phone, email=email)

    for attempt in range(_CREATE_ATTEMPTS):
        try:
            with transaction.atomic():
                return Candidate.objects.create(
                    code=_generate_code(), full_name=full_name, phone=phone, email=email
                )
        except IntegrityError:
            # A concurrent request inserted the same phone or email after the check above.
            _raise_if_duplicate(phone=phone, email=email)
            # Otherwise a concurrent request took the generated code: retry with a new one.
            if attempt == _CREATE_ATTEMPTS - 1:
                raise
    raise AssertionError("unreachable")


def candidate_delete(*, candidate: Candidate) -> None:
    """Soft delete: the candidate is hidden, their messages and delivery events are kept."""
    candidate.is_deleted = True
    candidate.save(update_fields=["is_deleted", "updated_at"])


def candidates_bulk_delete(*, candidate_ids: Iterable[UUID]) -> int:
    """Soft-delete the given candidates; unknown or already deleted ids are ignored.

    Returns the number of candidates deleted.
    """
    # update() skips auto_now, so updated_at is set explicitly to record when they were deleted.
    return Candidate.objects.filter(id__in=set(candidate_ids)).update(
        is_deleted=True, updated_at=timezone.now()
    )
