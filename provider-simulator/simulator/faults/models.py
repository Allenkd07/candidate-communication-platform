from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

MAX_LATENCY_MS = 30_000


class FaultConfig(models.Model):
    """Injected faults, a single row shared by the API process and the worker."""

    # Every API call answers 503 and health reports "down".
    outage = models.BooleanField(default=False)
    # Share of API calls that answer 503 at random.
    failure_rate = models.FloatField(
        default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    # Added to every API call before it is handled.
    latency_ms = models.PositiveIntegerField(
        default=0, validators=[MaxValueValidator(MAX_LATENCY_MS)]
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"outage={self.outage} failure_rate={self.failure_rate} latency_ms={self.latency_ms}"
