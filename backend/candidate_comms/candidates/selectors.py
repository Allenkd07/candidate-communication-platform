import re
from uuid import UUID

from django.db.models import OuterRef, Q, QuerySet, Subquery
from django.shortcuts import get_object_or_404

from candidate_comms.communications.models import Message

from .models import Candidate

_PHONE_SEPARATORS = re.compile(r"[\s()+\-]")


def candidate_list(*, search: str = "") -> QuerySet[Candidate]:
    """Candidates, newest first, annotated with their latest message.

    The table's "Last message" and "Status" columns come from these annotations instead of
    being stored on the candidate.
    """
    latest_message = Message.objects.filter(candidate=OuterRef("pk")).order_by("-created_at")
    queryset = Candidate.objects.annotate(
        last_message_at=Subquery(latest_message.values("created_at")[:1]),
        last_message_status=Subquery(latest_message.values("status")[:1]),
        last_message_body=Subquery(latest_message.values("body")[:1]),
    )

    search = search.strip()
    if search:
        number = _PHONE_SEPARATORS.sub("", search)
        match = Q(full_name__icontains=search) | Q(email__icontains=search) | Q(code__iexact=search)
        # Phones are stored as E.164, so "98765 43210" must match "+919876543210". Only a
        # purely numeric search is matched against phones, so "A1B2C3" never matches "...123...".
        if number.isdigit() and len(number) >= 3:
            match |= Q(phone__contains=number)
        queryset = queryset.filter(match)
    return queryset.order_by("-created_at")


def candidate_get(*, candidate_id: UUID) -> Candidate:
    return get_object_or_404(Candidate, id=candidate_id)
