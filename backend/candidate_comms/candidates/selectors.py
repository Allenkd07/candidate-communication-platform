import re
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from django.db.models import OuterRef, Q, QuerySet, Subquery
from django.shortcuts import get_object_or_404

from candidate_comms.communications.models import Message

from .models import Candidate

_PHONE_SEPARATORS = re.compile(r"[\s()+\-]")

# Status filter value for candidates who have never been messaged.
NO_MESSAGES = "none"


@dataclass(frozen=True)
class CandidateFilters:
    """Per-column table filters; empty values filter nothing."""

    name: str = ""
    phone: str = ""
    code: str = ""
    statuses: Collection[str] = field(default_factory=tuple)
    last_message_after: datetime | None = None
    last_message_before: datetime | None = None


def candidate_list(
    *, search: str = "", filters: CandidateFilters | None = None
) -> QuerySet[Candidate]:
    """Candidates, newest first, annotated with their latest message.

    The table's "Last message" and "Status" columns come from these annotations instead of
    being stored on the candidate, so their filters apply to the latest message only.
    """
    latest_message = Message.objects.filter(candidate=OuterRef("pk")).order_by("-created_at")
    queryset = Candidate.objects.annotate(
        last_message_at=Subquery(latest_message.values("created_at")[:1]),
        last_message_status=Subquery(latest_message.values("status")[:1]),
        last_message_body=Subquery(latest_message.values("body")[:1]),
        last_message_failure_reason=Subquery(latest_message.values("failure_reason")[:1]),
    )

    search = search.strip()
    if search:
        number = _PHONE_SEPARATORS.sub("", search)
        match = Q(full_name__icontains=search) | Q(email__icontains=search)
        # IDs are random, so only a prefix of 3+ characters is matched; shorter or mid-ID
        # fragments would match unrelated candidates.
        if len(search) >= 3:
            match |= Q(code__istartswith=search)
        # Phones are stored as E.164, so "98765 43210" must match "+919876543210". Only a
        # purely numeric search is matched against phones, so "A1B2C3" never matches "...123...".
        if number.isdigit() and len(number) >= 3:
            match |= Q(phone__contains=number)
        queryset = queryset.filter(match)
    if filters:
        queryset = queryset.filter(_filters_match(filters))
    return queryset.order_by("-created_at")


def _filters_match(filters: CandidateFilters) -> Q:
    match = Q()
    if name := filters.name.strip():
        match &= Q(full_name__icontains=name)
    if number := _PHONE_SEPARATORS.sub("", filters.phone):
        match &= Q(phone__contains=number)
    if code := filters.code.strip():
        match &= Q(code__icontains=code)
    if filters.statuses:
        statuses = set(filters.statuses)
        status_match = Q(last_message_status__in=statuses - {NO_MESSAGES})
        if NO_MESSAGES in statuses:
            status_match |= Q(last_message_status__isnull=True)
        match &= status_match
    if filters.last_message_after:
        match &= Q(last_message_at__gte=filters.last_message_after)
    if filters.last_message_before:
        match &= Q(last_message_at__lt=filters.last_message_before)
    return match


def candidate_get(*, candidate_id: UUID) -> Candidate:
    return get_object_or_404(Candidate, id=candidate_id)
