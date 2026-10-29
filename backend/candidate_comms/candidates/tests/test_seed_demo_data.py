import pytest
from django.core.management import call_command

from candidate_comms.candidates.management.commands.seed_demo_data import (
    CANDIDATES,
    TEST_NUMBER_CANDIDATES,
)
from candidate_comms.candidates.models import Candidate
from candidate_comms.communications.models import Message

pytestmark = pytest.mark.django_db


def test_seed_is_idempotent_and_replays_history() -> None:
    call_command("seed_demo_data")
    call_command("seed_demo_data")

    assert Candidate.objects.count() == len(CANDIDATES) + len(TEST_NUMBER_CANDIDATES)
    expected = {phone: status for _, phone, _, status in CANDIDATES if status is not None}
    actual = dict(Message.objects.values_list("candidate__phone", "status"))
    assert actual == expected


def test_reset_recreates_the_data() -> None:
    call_command("seed_demo_data")
    Candidate.objects.filter(phone=TEST_NUMBER_CANDIDATES[0][1]).delete()

    call_command("seed_demo_data", "--reset")

    assert Candidate.objects.count() == len(CANDIDATES) + len(TEST_NUMBER_CANDIDATES)
