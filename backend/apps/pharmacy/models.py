"""Medication catalog — Phase 1 minimal form (design §1): a picklist so
prescriptions are coded, never free-text-first. Phase 2 adds batches, the
stock ledger, and dispensing without touching this table's shape."""

from django.db import models

from apps.core.models import AuditedModel, ClinicScopedModel, TimeStampedModel


class Medication(AuditedModel, ClinicScopedModel, TimeStampedModel):
    class Form(models.TextChoices):
        TABLET = "tablet"
        CAPSULE = "capsule"
        SYRUP = "syrup"
        INJECTION = "injection"
        CREAM = "cream"
        DROPS = "drops"
        OTHER = "other"

    name = models.CharField(max_length=200)
    strength = models.CharField(max_length=50, blank=True)  # e.g. "500 mg"
    form = models.CharField(max_length=20, choices=Form.choices, default=Form.TABLET)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "strength"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "name", "strength", "form"], name="unique_medication"
            ),
        ]

    def __str__(self):
        label = f"{self.name} {self.strength}".strip()
        return f"{label} ({self.form})"
