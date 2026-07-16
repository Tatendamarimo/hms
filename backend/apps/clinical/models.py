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


class Prescription(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    """A prescription document issued from a consultation. Cancellation flips
    status (audited with reason); the record itself is never edited."""

    class Status(models.TextChoices):
        ISSUED = "issued"
        CANCELLED = "cancelled"

    consultation = models.ForeignKey(
        Consultation, on_delete=models.PROTECT, related_name="prescriptions"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ISSUED)

    def __str__(self):
        return f"Prescription #{self.pk} ({self.status})"


class PrescriptionItem(AuditedModel, ClinicScopedModel, TimeStampedModel):
    """Coded medication, or an explicit free-text fallback when the picklist
    lacks the drug (the fallback is the Admin's signal to grow the catalog)."""

    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="items"
    )
    medication = models.ForeignKey(
        "pharmacy.Medication", null=True, blank=True, on_delete=models.PROTECT,
        related_name="+",
    )
    medication_note = models.CharField(max_length=200, blank=True)
    dose = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration_days = models.PositiveSmallIntegerField()
    quantity = models.PositiveSmallIntegerField()
    instructions = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(medication__isnull=False) | ~models.Q(medication_note=""),
                name="prescription_item_coded_or_note",
            ),
        ]

    def __str__(self):
        return str(self.medication) if self.medication else self.medication_note

    @property
    def display_name(self) -> str:
        return str(self.medication) if self.medication else self.medication_note


class SickNote(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    consultation = models.ForeignKey(
        Consultation, on_delete=models.PROTECT, related_name="sick_notes"
    )
    unfit_from = models.DateField()
    unfit_to = models.DateField()
    remarks = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Sick note {self.unfit_from} – {self.unfit_to}"


class ReferralLetter(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    consultation = models.ForeignKey(
        Consultation, on_delete=models.PROTECT, related_name="referrals"
    )
    destination_facility = models.CharField(max_length=200)
    reason = models.TextField()

    def __str__(self):
        return f"Referral to {self.destination_facility}"


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
