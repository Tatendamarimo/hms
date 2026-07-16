"""Lab/imaging orders — Phase 1 minimal form (design §1): create, print,
bill, cancel. Phase 2 adds the work queue, sample tracking, results, and
verification WITHOUT changing these tables (status values are reserved there,
not here — a new status column stage arrives with the results workflow)."""

from django.db import models

from apps.core.models import AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel


class LabOrder(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    class Status(models.TextChoices):
        ORDERED = "ordered"
        CANCELLED = "cancelled"

    consultation = models.ForeignKey(
        "clinical.Consultation", on_delete=models.PROTECT, related_name="lab_orders"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ORDERED)
    instructions = models.TextField(blank=True)

    def __str__(self):
        return f"Lab order #{self.pk} ({self.status})"


class LabOrderItem(AuditedModel, ClinicScopedModel, TimeStampedModel):
    """price is snapshotted at ordering time (same rule as invoice lines)."""

    lab_order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name="items")
    service_item = models.ForeignKey(
        "billing.ServiceItem", on_delete=models.PROTECT, related_name="+"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.service_item.name
