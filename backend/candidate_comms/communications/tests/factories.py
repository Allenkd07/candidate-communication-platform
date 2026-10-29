from django.utils import timezone
from factory.declarations import LazyAttribute, LazyFunction, SubFactory
from factory.django import DjangoModelFactory

from candidate_comms.candidates.tests.factories import CandidateFactory
from candidate_comms.communications.models import Channel, Message, MessageBatch, MessageStatus


class MessageBatchFactory(DjangoModelFactory[MessageBatch]):
    class Meta:
        model = MessageBatch

    body = "Hello"
    channel = Channel.SMS
    gateway = "simulator"


class MessageFactory(DjangoModelFactory[Message]):
    class Meta:
        model = Message

    batch = SubFactory(MessageBatchFactory)
    candidate = SubFactory(CandidateFactory)
    channel = Channel.SMS
    gateway = "simulator"
    recipient = LazyAttribute(lambda message: message.candidate.phone)
    body = LazyAttribute(lambda message: message.batch.body)
    status = MessageStatus.QUEUED
    status_changed_at = LazyFunction(timezone.now)
