"""Patient registry (design §2.1). The Patient row is identity + longitudinal
data only — per-visit data lives on the Encounter (slice 3)."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel


class Patient(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    class Sex(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    class Status(models.TextChoices):
        ACTIVE = "active"
        DECEASED = "deceased"
        MERGED = "merged"  # merge tooling arrives in Phase 2; enum reserved now

    class BloodGroup(models.TextChoices):
        A_POS = "A+"
        A_NEG = "A-"
        B_POS = "B+"
        B_NEG = "B-"
        AB_POS = "AB+"
        AB_NEG = "AB-"
        O_POS = "O+"
        O_NEG = "O-"

    mrn = models.CharField(max_length=20, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()  # never store age (FRD §7)
    sex = models.CharField(max_length=1, choices=Sex.choices)
    national_id = models.CharField(max_length=40, blank=True, db_index=True)
    phone = models.CharField(max_length=30, blank=True, db_index=True)
    address = models.TextField(blank=True)
    next_of_kin_name = models.CharField(max_length=200, blank=True)
    next_of_kin_phone = models.CharField(max_length=30, blank=True)
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True)
    medical_aid_provider = models.CharField(max_length=100, blank=True)
    medical_aid_number = models.CharField(max_length=60, blank=True)
    consent_given_at = models.DateTimeField(editable=False)
    consent_captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        editable=False,
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(fields=["clinic", "mrn"], name="unique_mrn_per_clinic"),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.mrn})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        today = timezone.localdate()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class PatientAllergy(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    """Shown as a banner on every clinical screen (FRD §4.1). Corrections are
    void + re-enter, never edits."""

    class Severity(models.TextChoices):
        MILD = "mild"
        MODERATE = "moderate"
        SEVERE = "severe"

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="allergies")
    substance = models.CharField(max_length=200)
    reaction = models.CharField(max_length=200, blank=True)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "patient allergies"

    def __str__(self):
        return f"{self.substance} ({self.severity})"


class PatientCondition(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="conditions")
    condition = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.condition
