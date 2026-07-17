"""Slice 7: payment reversals and the refund flow (ADR-0003)."""

from decimal import Decimal

import pytest

from apps.billing import services
from apps.billing.models import Invoice, Payment
from apps.core.models import AuditLog

from .conftest import items_url, payments_url, reverse_url

pytestmark = pytest.mark.django_db


@pytest.fixture
def billed_invoice(receptionist, invoice, dressing):
    """Invoice carrying one 4.00 line."""
    response = receptionist.post(
        items_url(invoice), {"service_item": dressing.pk}, format="json"
    )
    assert response.status_code == 201, response.content
    return invoice


def pay(client, invoice, amount):
    response = client.post(
        payments_url(invoice), {"amount": amount, "method": "cash"}, format="json"
    )
    assert response.status_code == 201, response.content
    return response.json()


def test_cashier_reverses_a_payment_in_full(cashier, billed_invoice, claimed_visit):
    payment = pay(cashier, billed_invoice, "4.00")
    assert billed_invoice.status == Invoice.Status.PAID

    response = cashier.post(
        reverse_url(payment["id"]), {"reason": "Wrong invoice keyed"}, format="json"
    )
    assert response.status_code == 201, response.content
    reversal = response.json()
    assert reversal["reversal_of"] == payment["id"]
    assert reversal["receipt_number"].startswith("REC-")
    assert reversal["receipt_number"] != payment["receipt_number"]
    assert "Reversal of" in reversal["reference"]

    fresh = Invoice.objects.get(pk=billed_invoice.pk)
    assert fresh.paid_total == Decimal("0.00")
    assert fresh.status == Invoice.Status.UNPAID
    # Reversal never rewrites visit state retroactively
    claimed_visit.refresh_from_db()
    assert claimed_visit.status == "in_consultation"

    loud = [
        entry for entry in AuditLog.objects.filter(model_label="billing.Payment")
        if "payment_reversed" in entry.changes
    ]
    assert loud and loud[-1].changes["reason"] == "Wrong invoice keyed"


def test_partial_payment_reversal_walks_status_back(cashier, billed_invoice):
    first = pay(cashier, billed_invoice, "3.00")
    pay(cashier, billed_invoice, "1.00")
    assert billed_invoice.status == Invoice.Status.PAID

    cashier.post(reverse_url(first["id"]), {"reason": "typo"}, format="json")
    fresh = Invoice.objects.get(pk=billed_invoice.pk)
    assert fresh.paid_total == Decimal("1.00")
    assert fresh.status == Invoice.Status.PART_PAID


def test_reversal_requires_a_reason(cashier, billed_invoice):
    payment = pay(cashier, billed_invoice, "4.00")
    response = cashier.post(reverse_url(payment["id"]), {}, format="json")
    assert response.status_code == 400
    assert "reason" in response.json()["detail"]


def test_double_reversal_is_a_conflict(cashier, billed_invoice):
    payment = pay(cashier, billed_invoice, "4.00")
    assert cashier.post(
        reverse_url(payment["id"]), {"reason": "a"}, format="json"
    ).status_code == 201
    assert cashier.post(
        reverse_url(payment["id"]), {"reason": "b"}, format="json"
    ).status_code == 409


def test_a_reversal_cannot_be_reversed(cashier, billed_invoice):
    payment = pay(cashier, billed_invoice, "4.00")
    reversal = cashier.post(
        reverse_url(payment["id"]), {"reason": "a"}, format="json"
    ).json()
    response = cashier.post(reverse_url(reversal["id"]), {"reason": "b"}, format="json")
    assert response.status_code == 400
    assert "cannot itself" in response.json()["detail"]


def test_receptionist_cannot_reverse(receptionist, cashier, billed_invoice):
    payment = pay(cashier, billed_invoice, "4.00")
    response = receptionist.post(reverse_url(payment["id"]), {"reason": "x"}, format="json")
    assert response.status_code == 403


def test_named_permission_is_checked_beyond_the_role(cashier, billed_invoice, rec_user):
    """A user whose group lacks billing.reverse_payment is refused by the
    service even if a view let them through."""
    payment_id = pay(cashier, billed_invoice, "4.00")["id"]
    payment = Payment.objects.get(pk=payment_id)
    with pytest.raises(services.BillingPermissionError):
        services.reverse_payment(payment, by=rec_user, reason="x")


def test_cross_clinic_payment_is_invisible(
    user_factory, login, other_clinic, cashier, billed_invoice
):
    from apps.accounts import roles

    payment = pay(cashier, billed_invoice, "4.00")
    foreign_cashier = login(user_factory("cash.busi", roles.CASHIER, clinic=other_clinic))
    response = foreign_cashier.post(reverse_url(payment["id"]), {"reason": "x"}, format="json")
    assert response.status_code == 404


def test_reversal_receipt_is_printable(cashier, billed_invoice):
    payment = pay(cashier, billed_invoice, "4.00")
    reversal = cashier.post(
        reverse_url(payment["id"]), {"reason": "refund"}, format="json"
    ).json()
    page = cashier.get(f"/print/receipt/{reversal['id']}/")
    assert page.status_code == 200
    html = page.content.decode()
    assert "Reversal receipt" in html
    assert payment["receipt_number"] in html


def test_refund_flow_after_cancelled_lab_order(cashier, doctor, draft, invoice, malaria_test):
    """ADR-0003 end to end: pay → cancel order (surplus) → reverse → re-pay."""
    order = doctor.post(
        f"/api/v1/consultations/{draft['id']}/lab-orders/",
        {"service_items": [malaria_test.pk]},
        format="json",
    ).json()
    payment = pay(cashier, invoice, "5.00")
    assert Invoice.objects.get(pk=invoice.pk).status == Invoice.Status.PAID

    cancelled = doctor.post(
        f"/api/v1/lab-orders/{order['id']}/cancel/",
        {"reason": "Patient declined"},
        format="json",
    )
    assert cancelled.status_code == 200, cancelled.content
    surplus_invoice = Invoice.objects.get(pk=invoice.pk)
    assert surplus_invoice.total == Decimal("0.00")
    assert surplus_invoice.balance == Decimal("-5.00")  # money owed back

    # Full reversal returns the money; the log keeps every step
    reversed_ = cashier.post(
        reverse_url(payment["id"]), {"reason": "Refund — order cancelled"}, format="json"
    )
    assert reversed_.status_code == 201
    final = Invoice.objects.get(pk=invoice.pk)
    assert final.balance == Decimal("0.00")
    assert final.payments.count() == 2  # original + reversal, nothing deleted
