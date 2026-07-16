"""Billing operations. This module is the ONLY entry point other apps may use
to touch billing (module boundary rule) — encounters calls these functions,
never billing models directly."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.core.models import ClinicCounter

from .models import Invoice, InvoiceItem, Payment


class BillingError(Exception):
    """Domain rule violation — views map this to HTTP 400."""


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


def prepayment_satisfied(encounter) -> bool:
    """Payment-first gate (design §2.2): the encounter may proceed past
    'waiting' only when its invoice exists and carries no balance."""
    invoice = Invoice.objects.filter(encounter=encounter).first()
    return invoice is not None and invoice.balance <= 0
