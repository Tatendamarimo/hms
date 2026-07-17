"""Billing operations. This module is the ONLY entry point other apps may use
to touch billing (module boundary rule) — encounters calls these functions,
never billing models directly."""

from decimal import Decimal

from django.db import transaction
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.core.models import AuditLog, ClinicCounter

from .models import CashUp, Invoice, InvoiceItem, Payment


class BillingError(Exception):
    """Domain rule violation — views map this to HTTP 400."""


class BillingPermissionError(Exception):
    """Named-permission violation — views map this to HTTP 403."""


class BillingConflict(Exception):
    """The record moved on (already voided/reversed) — views map this to 409."""


def _require_open_encounter(invoice):
    if not invoice.encounter.is_open:
        raise BillingConflict(
            "The visit is closed; the invoice can no longer be adjusted."
        )


def _loud_audit(user, instance, changes):
    """Privileged billing actions get an explicit entry on top of the
    automatic model-diff audit (same pattern as allergy overrides)."""
    AuditLog.objects.create(
        user=user,
        clinic=instance.clinic,
        action=AuditLog.Action.UPDATE,
        model_label=instance._meta.label,
        object_pk=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=changes,
    )


def _number(clinic, kind: str, prefix: str) -> str:
    year = timezone.localdate().year
    sequence = ClinicCounter.next_value(clinic, f"{kind}:{year}")
    return f"{prefix}-{clinic.code.upper()}-{year}-{sequence:06d}"


def ensure_invoice(encounter, *, created_by) -> Invoice:
    invoice = Invoice.all_objects.filter(encounter=encounter).first()
    if invoice:
        return invoice
    with transaction.atomic():
        return Invoice.objects.create(
            clinic=encounter.clinic,
            encounter=encounter,
            number=_number(encounter.clinic, "invoice", "INV"),
            created_by=created_by,
        )


def add_service_line(
    invoice, *, service_item, created_by, quantity=1, lab_order=None
) -> InvoiceItem:
    """Price is snapshotted from the current ServicePrice — no free-text
    amounts anywhere in the system (design §2.5). `lab_order` links the line
    to its source record when the charge originates from an order."""
    price = service_item.current_price()
    if price is None:
        raise BillingError(
            f"'{service_item.name}' has no price set — the Admin must add one "
            "before it can be billed."
        )
    return InvoiceItem.objects.create(
        clinic=invoice.clinic,
        invoice=invoice,
        service_item=service_item,
        lab_order=lab_order,
        description=service_item.name,
        quantity=quantity,
        unit_price=price,
        created_by=created_by,
    )


def void_lines_for_lab_order(lab_order, *, by, reason: str) -> int:
    """Cancelling an order retracts its charges (design §2.4/slice 6)."""
    count = 0
    for item in InvoiceItem.objects.filter(lab_order=lab_order):
        item.void(by=by, reason=reason)
        count += 1
    return count


def record_payment(invoice, *, amount, method, received_by, reference="") -> Payment:
    """Locks the invoice row so two tills cannot both collect the same balance."""
    amount = Decimal(amount)
    if amount <= 0:
        raise BillingError("Payment amount must be positive.")
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if amount > locked.balance:
            raise BillingError(
                f"Payment of {amount} exceeds the outstanding balance of {locked.balance}. "
                "Overpayment is not accepted — give change at the desk."
            )
        return Payment.objects.create(
            clinic=locked.clinic,
            invoice=locked,
            amount=amount,
            method=method,
            reference=reference,
            receipt_number=_number(locked.clinic, "receipt", "REC"),
            received_by=received_by,
            created_by=received_by,
        )


def add_manual_line(invoice, *, service_item, by, quantity=1) -> InvoiceItem:
    """Desk-added catalog service (design §2.5). Locked like record_payment so
    the totals the desk sees are the totals that get billed."""
    if quantity < 1:
        raise BillingError("Quantity must be at least 1.")
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
        _require_open_encounter(locked)
        if service_item.clinic_id != locked.clinic_id:
            raise BillingError("Service belongs to a different clinic.")
        if not service_item.is_active:
            raise BillingError(f"'{service_item.name}' is inactive and cannot be billed.")
        return add_service_line(
            locked, service_item=service_item, created_by=by, quantity=quantity
        )


def apply_discount(invoice, *, by, amount, reason: str) -> InvoiceItem:
    """The sanctioned exception to catalog-priced-only lines: a desk-entered
    negative amount, permission-gated, with a structured mandatory reason."""
    reason = (reason or "").strip()
    if not reason:
        raise BillingError("A discount reason is required.")
    if not by.has_perm("billing.apply_discount"):
        raise BillingPermissionError("You do not have permission to apply discounts.")
    amount = Decimal(amount)
    if amount <= 0:
        raise BillingError("Discount amount must be positive.")
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
        _require_open_encounter(locked)
        if amount > locked.total:
            raise BillingError(
                f"Discount of {amount} exceeds the invoice total of {locked.total}."
            )
        if locked.total - amount < locked.paid_total:
            raise BillingError(
                "This discount would reduce the total below what has already "
                "been paid — reverse a payment first."
            )
        item = InvoiceItem.objects.create(
            clinic=locked.clinic,
            invoice=locked,
            description=f"Discount — {reason}",
            quantity=1,
            unit_price=-amount,
            item_type=InvoiceItem.ItemType.DISCOUNT,
            discount_reason=reason,
            created_by=by,
        )
        _loud_audit(by, item, {"discount_applied": str(amount), "reason": reason})
    return item


def void_line(item, *, by, reason: str) -> InvoiceItem:
    """Mistake correction for desk-added lines (incl. discounts). Lab lines
    are voided only through order cancellation, which keeps the order and its
    charges in step."""
    reason = (reason or "").strip()
    if not reason:
        raise BillingError("A void reason is required.")
    if item.lab_order_id is not None:
        raise BillingError(
            "Lab charges are retracted by cancelling the lab order, "
            "not by voiding the line."
        )
    with transaction.atomic():
        locked_invoice = Invoice.objects.select_for_update().get(pk=item.invoice_id)
        _require_open_encounter(locked_invoice)
        locked_item = InvoiceItem.all_objects.get(pk=item.pk)
        if locked_item.is_voided:
            raise BillingConflict("This line has already been voided.")
        if locked_invoice.total - locked_item.line_total < locked_invoice.paid_total:
            raise BillingError(
                "Voiding this line would leave the invoice below what has "
                "already been paid — reverse a payment first."
            )
        locked_item.void(by=by, reason=reason)
        _loud_audit(by, locked_item, {"line_voided": locked_item.description, "reason": reason})
    return locked_item


def reverse_payment(payment, *, by, reason: str) -> Payment:
    """Full reversal only (ADR-0003): a negative-effect row with its own
    receipt number. Partial refund = reverse in full, re-record the correct
    amount. The invoice lock serializes reversals against payment recording."""
    reason = (reason or "").strip()
    if not reason:
        raise BillingError("A reversal reason is required.")
    if not by.has_perm("billing.reverse_payment"):
        raise BillingPermissionError("You do not have permission to reverse payments.")
    if payment.reversal_of_id is not None:
        raise BillingError("A reversal cannot itself be reversed.")
    with transaction.atomic():
        locked_invoice = Invoice.objects.select_for_update().get(pk=payment.invoice_id)
        if Payment.objects.filter(reversal_of=payment).exists():
            raise BillingConflict("This payment has already been reversed.")
        reversal = Payment.objects.create(
            clinic=locked_invoice.clinic,
            invoice=locked_invoice,
            amount=payment.amount,
            method=payment.method,
            reference=f"Reversal of {payment.receipt_number}",
            receipt_number=_number(locked_invoice.clinic, "receipt", "REC"),
            received_by=by,
            created_by=by,
            reversal_of=payment,
        )
        _loud_audit(
            by,
            reversal,
            {
                "payment_reversed": payment.receipt_number,
                "amount": str(payment.amount),
                "reason": reason,
            },
        )
    return reversal


def _drawer_queryset(clinic, cashier):
    """The open drawer: this cashier's cash rows not yet covered by a
    cash-up. Reversal rows are included — cash handed back left the drawer."""
    return Payment.objects.filter(
        clinic=clinic,
        received_by=cashier,
        method=Payment.Method.CASH,
        cash_up__isnull=True,
    ).order_by("created_at", "pk")


def _drawer_expected(payments) -> Decimal:
    return sum(
        ((-p.amount if p.reversal_of_id else p.amount) for p in payments),
        Decimal("0.00"),
    )


def _last_cash_up(clinic, cashier):
    return (
        CashUp.objects.filter(clinic=clinic, cashier=cashier)
        .order_by("-period_end")
        .first()
    )


def drawer_preview(clinic, cashier) -> dict:
    """What POST close would reconcile right now — computed, never stored."""
    payments = list(_drawer_queryset(clinic, cashier))
    last = _last_cash_up(clinic, cashier)
    if last is not None:
        period_start = last.period_end
    else:
        period_start = payments[0].created_at if payments else None
    return {
        "expected_total": _drawer_expected(payments),
        "payment_count": len(payments),
        "period_start": period_start,
        "previous_cash_up_at": last.period_end if last else None,
        "payments": payments,
    }


def close_cash_up(clinic, *, cashier, counted_total, notes="") -> CashUp:
    """End-of-day reconciliation (FRD §5.7): count the drawer, record the
    variance, stamp the covered payments so the next period starts clean.
    Atomic — the row is born closed; there is no half-open cash-up."""
    notes = (notes or "").strip()
    counted_total = Decimal(counted_total)
    if counted_total < 0:
        raise BillingError("The counted total cannot be negative.")
    with transaction.atomic():
        payments = list(_drawer_queryset(clinic, cashier).select_for_update())
        if not payments:
            raise BillingError("There are no cash payments to cash up.")
        expected = _drawer_expected(payments)
        if counted_total != expected and not notes:
            raise BillingError(
                "Counted and expected totals differ — a note explaining "
                "the variance is required."
            )
        last = _last_cash_up(clinic, cashier)
        cash_up = CashUp.objects.create(
            clinic=clinic,
            cashier=cashier,
            period_start=last.period_end if last else payments[0].created_at,
            period_end=timezone.now(),
            expected_total=expected,
            counted_total=counted_total,
            notes=notes,
            status=CashUp.Status.CLOSED,
            created_by=cashier,
        )
        # Individual saves, not queryset.update(): the stamp is the one
        # sanctioned mutation of a Payment row and must hit the audit trail.
        for payment in payments:
            payment.cash_up = cash_up
            payment.save(update_fields=["cash_up", "updated_at"])
    return cash_up


def unpaid_invoices(clinic):
    """Invoices carrying a balance, aggregated in the database so the view
    never loads paid history (FRD §5.7 unpaid balances view). Mirrors the
    Invoice.total / paid_total properties: voided lines excluded, reversed
    payments and their reversal rows cancel out."""
    money = DecimalField(max_digits=10, decimal_places=2)
    line_totals = (
        InvoiceItem.objects.filter(invoice=OuterRef("pk"))
        .order_by()
        .values("invoice")
        .annotate(t=Sum(F("unit_price") * F("quantity"), output_field=money))
        .values("t")
    )
    paid_totals = (
        Payment.objects.filter(
            invoice=OuterRef("pk"),
            reversal_of__isnull=True,
            reversed_by__isnull=True,
        )
        .order_by()
        .values("invoice")
        .annotate(t=Sum("amount"))
        .values("t")
    )
    zero = Value(Decimal("0.00"))
    return (
        Invoice.objects.filter(clinic=clinic)
        .annotate(
            total_amount=Coalesce(Subquery(line_totals), zero, output_field=money),
            paid_amount=Coalesce(Subquery(paid_totals), zero, output_field=money),
        )
        .annotate(
            outstanding=ExpressionWrapper(
                F("total_amount") - F("paid_amount"), output_field=money
            )
        )
        .filter(outstanding__gt=0)
        .select_related("encounter__patient")
        .order_by("-outstanding", "pk")
    )


def prepayment_satisfied(encounter) -> bool:
    """Payment-first gate (design §2.2): the encounter may proceed past
    'waiting' only when its invoice exists and carries no balance."""
    invoice = Invoice.objects.filter(encounter=encounter).first()
    return invoice is not None and invoice.balance <= 0
