import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from candidate_comms.candidates.validators import (
    normalize_email,
    normalize_full_name,
    normalize_phone,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Taylor   Swift ", "Taylor Swift"),
        ("Mary-Jane O'Neil", "Mary-Jane O'Neil"),
        ("Martin Luther King Jr.", "Martin Luther King Jr."),
        ("José Ñúñez", "José Ñúñez"),
    ],
)
def test_valid_names_are_trimmed(raw: str, expected: str) -> None:
    assert normalize_full_name(raw) == expected


@pytest.mark.parametrize("raw", ["A", "   ", "R2D2", "Taylor_Swift", "-Taylor", "x" * 101])
def test_invalid_names_are_rejected(raw: str) -> None:
    with pytest.raises(ValidationError):
        normalize_full_name(raw)


@override_settings(DEFAULT_PHONE_REGION="IN")
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9845012345", "+919845012345"),
        ("098450 12345", "+919845012345"),
        ("+91 98450-12345", "+919845012345"),
        ("+44 7911 123456", "+447911123456"),
    ],
)
def test_mobile_numbers_are_stored_as_e164(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@override_settings(DEFAULT_PHONE_REGION="IN")
@pytest.mark.parametrize("raw", ["", "12345", "not a number", "+91 1234567890", "+44 20 7946 0958"])
def test_invalid_or_non_mobile_numbers_are_rejected(raw: str) -> None:
    with pytest.raises(ValidationError):
        normalize_phone(raw)


def test_emails_are_lower_cased() -> None:
    assert normalize_email("  Taylor.Swift@Example.COM ") == "taylor.swift@example.com"
