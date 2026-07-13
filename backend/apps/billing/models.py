"""Service catalog and versioned price list (design §2.5).

Prices are never edited or deleted: a price change is a new ServicePrice row
with a later effective_from. The current price is the newest row whose
effective_from is not in the future. Invoice lines (slice 7) snapshot the
price at creation, so historical invoices are immune to catalog changes."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import AuditedModel, ClinicScopedModel, TimeStampedModel


class ServiceItem(AuditedModel, ClinicScopedModel, TimeStampedModel):
    class Type(models.TextChoices):
        CONSULTATION = "consultation"
        LAB = "lab"
        IMAGING = "imaging"
        PROCEDURE = "procedure"
        OTHER = "other"

    code = models.SlugField(max_length=40)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=Type.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["clinic", "code"], name="unique_service_per_clinic"),
        ]

    def current_price(self, on=None):
        on = on or timezone.localdate()
        row = self.prices.filter(effective_from__lte=on).order_by("-effective_from").first()
        return row.price if row else None

    def __str__(self):
        return f"{self.code} — {self.name}"


class ServicePrice(AuditedModel, ClinicScopedModel, TimeStampedModel):
    service = models.ForeignKey(ServiceItem, on_delete=models.PROTECT, related_name="prices")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    effective_from = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "effective_from"], name="one_price_per_service_per_day"
            ),
        ]

    def __str__(self):
        return f"{self.service.code} @ {self.price} from {self.effective_from}"
