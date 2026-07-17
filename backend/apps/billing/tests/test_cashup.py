"""Slice 8: end-of-day cash-up per cashier (FRD §5.7)."""

from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.billing.models import CashUp, Payment
from apps.core.models import AuditLog

from .conftest import items_url, payments_url, reverse_url

pytestmark = pytest.mark.django_db

CASHUP = "/api/v1/billing/cashup/"


@pytest.fixture
def big_invoice(receptionist, invoice, dressing):
    """Invoice with room for several payments (3 × 4.00 = 12.00)."""
    response = receptionist.post(
        items_url(invoice), {"service_item": dressing.pk, "quantity": 3}, format="json"
    )
    assert response.status_code == 201, response.content
    return invoice


def pay(client, invoice, amount, method="cash"):
    response = client.post(
        payments_url(invoice), {"amount": amount, "method": method}, format="json"
    )
    assert response.status_code == 201, response.content
    return response.json()


def close(client, counted, notes=""):
    return client.post(
        CASHUP, {"counted_total": counted, "notes": notes}, format="json"
    )


# --- edges first ---


def test_cashup_is_cashier_only(receptionist, admin, nurse, doctor):
    for client in (receptionist, admin, nurse, doctor):
        assert client.get(CASHUP).status_code == 403
        assert close(client, "0.00").status_code == 403


def test_empty_drawer_cannot_be_closed(cashier):
    response = close(cashier, "0.00")
    assert response.status_code == 400
    assert "no cash payments" in response.json()["detail"]


def test_variance_requires_notes(cashier, big_invoice):
    pay(cashier, big_invoice, "4.00")
    response = close(cashier, "3.50")
    assert response.status_code == 400
    assert "variance" in response.json()["detail"]

    explained = close(cashier, "3.50", notes="Short 0.50 — till float error")
    assert explained.status_code == 201, explained.content
    body = explained.json()
    assert body["variance"] == "-0.50"
    assert "float error" in body["notes"]


def test_db_refuses_an_unexplained_variance(clinic, cashier_user):
    now = timezone.now()
    with pytest.raises(IntegrityError):
        CashUp.objects.create(
            clinic=clinic, cashier=cashier_user,
            period_start=now, period_end=now,
            expected_total=Decimal("5.00"), counted_total=Decimal("4.00"),
            notes="", created_by=cashier_user,
        )


def test_negative_counted_total_is_rejected(cashier, big_invoice):
    pay(cashier, big_invoice, "4.00")
    response = close(cashier, "-1.00")
    assert response.status_code == 400


# --- the drawer ---


def test_preview_counts_only_this_cashiers_unstamped_cash(
    cashier, receptionist, big_invoice
):
    pay(cashier, big_invoice, "3.00")
    pay(cashier, big_invoice, "1.00")
    pay(cashier, big_invoice, "5.00", method="ecocash")
    pay(receptionist, big_invoice, "2.00")  # someone else's drawer

    preview = cashier.get(CASHUP).json()
    assert preview["expected_total"] == "4.00"
    assert preview["payment_count"] == 2
    assert preview["previous_cash_up_at"] is None
    receipts = {p["receipt_number"] for p in preview["payments"]}
    assert len(receipts) == 2
    assert CashUp.objects.count() == 0  # preview is computed, never stored


def test_close_stamps_payments_and_resets_the_drawer(cashier, big_invoice):
    pay(cashier, big_invoice, "3.00")
    pay(cashier, big_invoice, "1.00")

    response = close(cashier, "4.00")
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["expected_total"] == "4.00"
    assert body["variance"] == "0.00"
    assert body["status"] == "closed"

    cash_up = CashUp.objects.get(pk=body["id"])
    stamped = Payment.objects.filter(cash_up=cash_up)
    assert stamped.count() == 2

    fresh = cashier.get(CASHUP).json()
    assert fresh["expected_total"] == "0.00"
    assert fresh["payment_count"] == 0
    assert fresh["previous_cash_up_at"] is not None

    again = close(cashier, "0.00")
    assert again.status_code == 400  # nothing left to cash up


def test_second_period_covers_only_new_payments(cashier, big_invoice):
    pay(cashier, big_invoice, "3.00")
    first = close(cashier, "3.00").json()

    pay(cashier, big_invoice, "1.00")
    second = close(cashier, "1.00")
    assert second.status_code == 201, second.content
    body = second.json()
    assert body["expected_total"] == "1.00"
    assert body["period_start"] == first["period_end"]


def test_same_period_reversal_nets_to_zero(cashier, big_invoice):
    payment = pay(cashier, big_invoice, "4.00")
    reversed_ = cashier.post(
        reverse_url(payment["id"]), {"reason": "keyed wrong"}, format="json"
    )
    assert reversed_.status_code == 201, reversed_.content

    preview = cashier.get(CASHUP).json()
    assert preview["expected_total"] == "0.00"
    assert preview["payment_count"] == 2  # both rows are drawer events

    response = close(cashier, "0.00")
    assert response.status_code == 201, response.content
    assert Payment.objects.filter(cash_up__isnull=False).count() == 2


def test_cross_period_reversal_makes_the_drawer_negative(cashier, big_invoice):
    payment = pay(cashier, big_invoice, "4.00")
    close(cashier, "4.00")

    cashier.post(reverse_url(payment["id"]), {"reason": "refund"}, format="json")
    preview = cashier.get(CASHUP).json()
    assert preview["expected_total"] == "-4.00"

    response = close(cashier, "0.00", notes="Refund paid out of counted drawer")
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["expected_total"] == "-4.00"
    assert body["variance"] == "4.00"


# --- audit ---


def test_close_is_audited_on_the_cashup_and_the_stamped_payment(cashier, big_invoice):
    payment_id = pay(cashier, big_invoice, "4.00")["id"]
    cash_up_id = close(cashier, "4.00").json()["id"]

    assert AuditLog.objects.filter(
        model_label="billing.CashUp",
        object_pk=str(cash_up_id),
        action=AuditLog.Action.CREATE,
    ).exists()
    stamp = AuditLog.objects.filter(
        model_label="billing.Payment", object_pk=str(payment_id),
        action=AuditLog.Action.UPDATE,
    ).last()
    assert stamp is not None and "cash_up" in stamp.changes
