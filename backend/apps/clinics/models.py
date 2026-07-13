from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, TimeStampedModel


class Clinic(AuditedModel, TimeStampedModel):
    """A tenant. Every business record in the system belongs to exactly one
    clinic (FRD §7.1). v1 deploys with a single clinic; the schema does not
    know that."""

    name = models.CharField(max_length=200)
    code = models.SlugField(max_length=30, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClinicMembership(AuditedModel, TimeStampedModel):
    """Grants a user access to a clinic. Roles are global Django groups;
    membership controls *where* those roles apply (FRD §3)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clinic_memberships",
    )
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="memberships")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "clinic"], name="unique_user_clinic"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.clinic}"
