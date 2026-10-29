from django.db import models

from candidate_comms.core.models import BaseModel

CANDIDATE_CODE_LENGTH = 6


class ActiveCandidateManager(models.Manager["Candidate"]):
    def get_queryset(self) -> models.QuerySet["Candidate"]:
        return super().get_queryset().filter(is_deleted=False)


class Candidate(BaseModel):
    # Short public identifier shown in the UI, e.g. "A1B2C3". Never reused, even after deletion.
    code = models.CharField(max_length=CANDIDATE_CODE_LENGTH, unique=True, editable=False)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=16, help_text="E.164, e.g. +919876543210")
    email = models.EmailField(help_text="Stored lower-cased")
    # Soft delete: the candidate leaves every list and lookup, but their message history is kept.
    is_deleted = models.BooleanField(default=False)

    # Deleted candidates are hidden by default; all_objects also includes them.
    objects = ActiveCandidateManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Only active candidates must be unique, so a deleted candidate can be added again.
            models.UniqueConstraint(
                fields=["phone"],
                condition=models.Q(is_deleted=False),
                name="unique_active_candidate_phone",
            ),
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(is_deleted=False),
                name="unique_active_candidate_email",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.code})"
