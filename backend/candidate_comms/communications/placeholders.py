"""Candidate details in message text, written as {{first_name}}, filled in per recipient at send."""

import re
from collections.abc import Callable

from candidate_comms.candidates.models import Candidate

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z_]+)\s*\}\}")

FIELDS: dict[str, Callable[[Candidate], str]] = {
    "first_name": lambda candidate: candidate.full_name.split()[0],
    "full_name": lambda candidate: candidate.full_name,
}


def unknown_placeholders(text: str) -> list[str]:
    return sorted({name for name in PLACEHOLDER.findall(text) if name not in FIELDS})


def unknown_placeholder_error(text: str) -> str | None:
    """Recruiter-facing message for placeholders that can't be filled in, or None."""
    unknown = unknown_placeholders(text)
    if not unknown:
        return None
    allowed = ", ".join(f"{{{{{name}}}}}" for name in FIELDS)
    found = ", ".join(f"{{{{{name}}}}}" for name in unknown)
    return f"Unknown placeholder {found}. Use {allowed}."


def render(text: str, candidate: Candidate) -> str:
    return PLACEHOLDER.sub(lambda match: FIELDS[match.group(1)](candidate), text)
