import re

import phonenumbers
from django.conf import settings
from django.core.exceptions import ValidationError

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 100
# Letters (any script) separated by single spaces, dots, apostrophes or hyphens.
_NAME_PATTERN = re.compile(r"^[^\W\d_]+(?:[ .'\-]+[^\W\d_]+)*\.?$")
_MOBILE_TYPES = {
    phonenumbers.PhoneNumberType.MOBILE,
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
}


def normalize_full_name(value: str) -> str:
    name = " ".join(value.split())
    if not NAME_MIN_LENGTH <= len(name) <= NAME_MAX_LENGTH:
        raise ValidationError(
            f"Name must be {NAME_MIN_LENGTH} to {NAME_MAX_LENGTH} characters long."
        )
    if not _NAME_PATTERN.match(name):
        raise ValidationError(
            "Name can contain only letters, spaces, dots, apostrophes and hyphens."
        )
    return name


def normalize_phone(value: str) -> str:
    """Parse a mobile number (national numbers use DEFAULT_PHONE_REGION) and return E.164."""
    try:
        number = phonenumbers.parse(value, settings.DEFAULT_PHONE_REGION)
    except phonenumbers.NumberParseException as exc:
        raise ValidationError("Enter a valid mobile number.") from exc
    if (
        not phonenumbers.is_valid_number(number)
        or phonenumbers.number_type(number) not in _MOBILE_TYPES
    ):
        raise ValidationError("Enter a valid mobile number.")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def normalize_email(value: str) -> str:
    return value.strip().lower()
