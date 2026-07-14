"""Consultations — the append-only heart of the system (design §2.4).

A signed consultation is a legal clinical document. Immutability is enforced
HERE, at the model layer, not in views: any code path that tries to write a
signed row (other than voiding it) raises. Corrections are versioned
amendments chained via a OneToOne `amended_from`, so the database itself
guarantees a version can be amended at most once.
"""

from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel


class SignedConsultationImmutable(Exception):
    """Raised on any attempt to modify a signed consultation."""


class Diagnosis(AuditedModel, TimeStampedModel):
    """Global ICD-10 reference catalog (deliberately NOT clinic-scoped).
    Seeded from apps/clinical/data/icd10_subset.csv by `seed_diagnoses`;
    expanding coverage is a data change, never a schema change."""

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "diagnoses"

    def __str__(self):
        return f"{self.code} {self.name}"


class Consultation(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft"
        SIGNED = "signed"

    # Fields a signed row may still legally change (void = retraction, FRD §7.1)
    _SIGNED_MUTABLE_FIELDS = frozenset({"voided_at", "voided_by", "void_reason", "updated_at"})

    encounter = models.ForeignKey(
        "encounters.Encounter", on_delete=models.PROTECT, related_name="consultations"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="consultations"
    )
    presenting_complaint = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    signed_at = models.DateTimeField(null=True, blank=True, editable=False)
    version = models.PositiveSmallIntegerField(default=1, editable=False)
    amended_from = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="amended_by",
        editable=False,
    )
    amendment_reason = models.TextField(blank=True, editable=False)

    class Meta:
        ordering = ["version"]
        constraints = [
            models.UniqueConstraint(
                fields=["encounter"],
                condition=models.Q(amended_from__isnull=True, voided_at__isnull=True),
                name="one_root_consultation_per_encounter",
            ),
        ]

    def __str__(self):
        return f"Consultation v{self.version} ({self.status}) for encounter #{self.encounter_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            previous_status = (
                type(self).all_objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )
            if previous_status == self.Status.SIGNED:
                update_fields = kwargs.get("update_fields")
                if update_fields is None or not set(update_fields) <= self._SIGNED_MUTABLE_FIELDS:
                    raise SignedConsultationImmutable(
                        "A signed consultation is a legal clinical document and cannot be "
                        "modified. Create an amendment instead."
                    )
        super().save(*args, **kwargs)

    @property
    def is_amended(self) -> bool:
        return type(self).all_objects.filter(amended_from=self).exists()


class ConsultationDiagnosis(AuditedModel, ClinicScopedModel, TimeStampedModel):
    """Coded diagnosis and/or free text — at least one is required (DB-enforced).
    Editable only while the parent consultation is a draft; amendments receive
    copies, so signed history is never shared mutable state."""

    consultation = models.ForeignKey(
        Consultation, on_delete=models.CASCADE, related_name="diagnoses"
    )
    diagnosis = models.ForeignKey(
        Diagnosis, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    free_text = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "consultation diagnoses"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(diagnosis__isnull=False) | ~models.Q(free_text=""),
                name="diagnosis_coded_or_free_text",
            ),
        ]

    def __str__(self):
        return str(self.diagnosis) if self.diagnosis else self.free_text
