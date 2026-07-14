"""The Encounter — the spine of every visit (design §2.2). All clinical and
financial records for a visit hang off this row; its status drives the queue."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel


class Encounter(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    class Type(models.TextChoices):
        WALK_IN = "walk_in"
        FOLLOW_UP = "follow_up"
        EMERGENCY = "emergency"
        # Reserved so Phases 3+ add no enum migration:
        APPOINTMENT = "appointment"
        ANC = "anc"

    class Status(models.TextChoices):
        WAITING = "waiting"
        IN_TRIAGE = "in_triage"
        AWAITING_DOCTOR = "awaiting_doctor"
        IN_CONSULTATION = "in_consultation"
        # Reserved for Phase 2 loops:
        AT_LAB = "at_lab"
        AT_PHARMACY = "at_pharmacy"
        AWAITING_PAYMENT = "awaiting_payment"
        CLOSED = "closed"
        LWBS = "left_without_being_seen"

    OPEN_STATUSES = (
        Status.WAITING,
        Status.IN_TRIAGE,
        Status.AWAITING_DOCTOR,
        Status.IN_CONSULTATION,
        Status.AT_LAB,
        Status.AT_PHARMACY,
        Status.AWAITING_PAYMENT,
    )

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="encounters"
    )
    type = models.CharField(max_length=15, choices=Type.choices, default=Type.WALK_IN)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.WAITING)
    arrived_at = models.DateTimeField(default=timezone.now, editable=False)
    closed_at = models.DateTimeField(null=True, blank=True, editable=False)
    assigned_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assigned_encounters",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["arrived_at"]
        permissions = [
            ("close_with_balance", "Can close an encounter with an outstanding balance"),
        ]
        indexes = [models.Index(fields=["clinic", "status"])]

    def __str__(self):
        return f"{self.patient} — {self.get_status_display()} ({self.arrived_at:%Y-%m-%d})"

    @property
    def is_open(self) -> bool:
        return self.status in self.OPEN_STATUSES
