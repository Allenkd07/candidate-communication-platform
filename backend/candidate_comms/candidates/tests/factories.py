from factory.declarations import Sequence
from factory.django import DjangoModelFactory

from candidate_comms.candidates.models import Candidate


class CandidateFactory(DjangoModelFactory[Candidate]):
    class Meta:
        model = Candidate

    code = Sequence(lambda n: f"C{n:05d}")
    full_name = Sequence(lambda n: f"Candidate {chr(65 + n % 26)}")
    phone = Sequence(lambda n: f"+9198450{n:05d}")
    email = Sequence(lambda n: f"candidate{n}@example.com")
