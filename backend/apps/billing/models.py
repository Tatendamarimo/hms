"""Service catalog and versioned price list (design §2.5).

Prices are never edited or deleted: a price change is a new ServicePrice row
with a later effective_from. The current price is the newest row whose
effective_from is not in the future. Invoice lines (slice 7) snapshot the
price at creation, so historical invoices are immune to catalog changes."""

from decimal import Decimal

from django.conf import settings as django_settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import (
    AuditedModel,
    ClinicScopedModel,
    SoftDeleteModel,
    TimeStampedModel,
)


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


class Invoice(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    """One invoice per encounter (design §2.5). Status is ALWAYS derived from
    payments — never stored. Slice 3 ships the minimal model needed by the
    payment-first check-in flow; discounts/reversals UI arrive in slice 7."""

    class Status(models.TextChoices):
        UNPAID = "unpaid"
        PART_PAID = "part_paid"
        PAID = "paid"

    encounter = models.OneToOneField(
        "encounters.Encounter", on_delete=models.PROTECT, related_name="invoice"
    )
    number = models.CharField(max_length=30, editable=False)
    issued_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["clinic", "number"], name="unique_invoice_number"),
        ]
        permissions = [
            ("apply_discount", "Can apply a discount to an invoice"),
        ]

    def __str__(self):
        return self.number

    @property
    def total(self) -> Decimal:
        return sum((item.line_total for item in self.items.all()), Decimal("0.00"))

    @property
    def paid_total(self) -> Decimal:
        payments = list(self.payments.all())
        reversed_ids = {p.reversal_of_id for p in payments if p.reversal_of_id}
        return sum(
            (p.amount for p in payments if p.reversal_of_id is None and p.pk not in reversed_ids),
            Decimal("0.00"),
        )

    @property
    def balance(self) -> Decimal:
        return self.total - self.paid_total

    @property
    def status(self) -> str:
        if self.paid_total <= 0:
            return self.Status.UNPAID
        return self.Status.PAID if self.balance <= 0 else self.Status.PART_PAID


class InvoiceItem(AuditedModel, ClinicScopedModel, SoftDeleteModel, TimeStampedModel):
    """unit_price is snapshotted from ServicePrice at creation — later price
    changes never touch existing invoices. Source links: lab_order only in
    Phase 1 (the consultation link is dead per ADR-0002; dispense arrives with
    Phase 2 pharmacy). Discount lines are the sanctioned exception to
    catalog-priced-only: negative amount, permission-gated, structured reason."""

    class ItemType(models.TextChoices):
        SERVICE = "service"
        DISCOUNT = "discount"

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="items")
    service_item = models.ForeignKey(
        ServiceItem, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    # Source links (design §2.5): every line points at what earned it.
    lab_order = models.ForeignKey(
        "laboratory.LabOrder", null=True, blank=True, on_delete=models.PROTECT,
        related_name="invoice_items",
    )
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    item_type = models.CharField(
        max_length=10, choices=ItemType.choices, default=ItemType.SERVICE
    )
    discount_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="discount_lines_negative_sourceless_reasoned",
                condition=(
                    ~models.Q(item_type="discount")
                    | (
                        models.Q(unit_price__lt=0)
                        & models.Q(service_item__isnull=True)
                        & models.Q(lab_order__isnull=True)
                        & ~models.Q(discount_reason="")
                    )
                ),
            ),
            models.CheckConstraint(
                name="service_lines_nonnegative_unreasoned",
                condition=(
                    ~models.Q(item_type="service")
                    | (
                        models.Q(unit_price__gte=0)
                        & models.Q(discount_reason="")
                    )
                ),
            ),
        ]

    def __str__(self):
        return f"{self.description} x{self.quantity}"

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class Payment(AuditedModel, ClinicScopedModel, TimeStampedModel):
    """Append-only — deliberately NOT soft-deletable (design §2.5). Mistakes
    are corrected by reversal rows (slice 7), never by editing history."""

    class Method(models.TextChoices):
        CASH = "cash"
        ECOCASH = "ecocash"
        CARD = "card"
        OTHER = "other"

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    method = models.CharField(max_length=10, choices=Method.choices)
    reference = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=30, editable=False)
    received_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
        editable=False,
    )
    reversal_of = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversed_by"
    )
    cash_up = models.ForeignKey(
        "CashUp", null=True, blank=True, on_delete=models.PROTECT,
        related_name="payments", editable=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["clinic", "receipt_number"], name="unique_receipt"),
        ]
        permissions = [
            ("reverse_payment", "Can reverse a recorded payment"),
        ]

    def __str__(self):
        return f"{self.receipt_number} {self.amount} ({self.method})"


class CashUp(AuditedModel, ClinicScopedModel, TimeStampedModel):
    """End-of-day drawer reconciliation per cashier (FRD §5.7): expected vs
    counted, variance recorded. Append-only like Payment — a cash-up records
    a count that happened; a wrong count is explained in notes, never edited
    away. Rows are created already closed by services.close_cash_up: the
    'open drawer' is simply the cashier's cash payments not yet stamped with
    a cash_up FK, so no open row accumulates state."""

    class Status(models.TextChoices):
        OPEN = "open"
        CLOSED = "closed"

    cashier = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="cash_ups", editable=False,
    )
    period_start = models.DateTimeField(editable=False)
    period_end = models.DateTimeField(editable=False)
    # Reversal rows count negative, so a drawer can owe money overall.
    expected_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    counted_total = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.CLOSED
    )

    class Meta:
        ordering = ["-period_end"]
        constraints = [
            models.CheckConstraint(
                name="nonzero_variance_needs_notes",
                condition=(
                    models.Q(counted_total=models.F("expected_total"))
                    | ~models.Q(notes="")
                ),
            ),
        ]

    @property
    def variance(self) -> Decimal:
        return self.counted_total - self.expected_total

    def __str__(self):
        return f"Cash-up {self.cashier} @ {self.period_end:%Y-%m-%d %H:%M}"
