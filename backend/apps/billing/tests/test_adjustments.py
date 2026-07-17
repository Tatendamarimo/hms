"""Slice 7: manual invoice lines, discounts, and line voiding."""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.billing.models import InvoiceItem, ServicePrice
from apps.core.models import AuditLog

from .conftest import items_url, void_url

pytestmark = pytest.mark.django_db


def add_line(client, invoice, service, quantity=1):
    return client.post(
        items_url(invoice),
        {"service_item": service.pk, "quantity": quantity},
        format="json",
    )


def add_discount(client, invoice, amount, reason="Staff courtesy"):
    return client.post(
        items_url(invoice),
        {"item_type": "discount", "amount": amount, "reason": reason},
        format="json",
    )


# --- manual catalog lines ---


def test_receptionist_adds_catalog_line_with_price_snapshot(receptionist, invoice, dressing):
    response = add_line(receptionist, invoice, dressing)
    assert response.status_code == 201, response.content
    line = response.json()
    assert line["unit_price"] == "4.00"
    assert line["item_type"] == "service"

    # A later price change never touches the billed line
    ServicePrice.objects.create(
        clinic=dressing.clinic, service=dressing, price="9.00",
        effective_from=timezone.localdate() + timezone.timedelta(days=1),
    )
    assert invoice.items.get(pk=line["id"]).unit_price == Decimal("4.00")


def test_quantity_multiplies_the_line_total(cashier, invoice, dressing):
    response = add_line(cashier, invoice, dressing, quantity=3)
    assert response.status_code == 201
    assert response.json()["line_total"] == "12.00"
    assert invoice.total == Decimal("12.00")


def test_unpriced_service_is_rejected(receptionist, invoice, clinic):
    from apps.billing.models import ServiceItem

    bare = ServiceItem.objects.create(
        clinic=clinic, code="proc-bare", name="Unpriced", type=ServiceItem.Type.PROCEDURE
    )
    response = add_line(receptionist, invoice, bare)
    assert response.status_code == 400
    assert "no price" in response.json()["detail"]


def test_inactive_service_is_rejected(receptionist, invoice, dressing):
    dressing.is_active = False
    dressing.save()
    response = add_line(receptionist, invoice, dressing)
    assert response.status_code == 400
    assert "inactive" in response.json()["detail"]


def test_foreign_clinic_service_is_rejected(receptionist, invoice, other_clinic):
    from apps.billing.models import ServiceItem

    from .conftest import _priced_service

    foreign = _priced_service(
        other_clinic, "proc-x", "Foreign", ServiceItem.Type.PROCEDURE, "2.00"
    )
    response = add_line(receptionist, invoice, foreign)
    assert response.status_code == 400
    assert "different clinic" in response.json()["detail"]


def test_clinical_roles_cannot_touch_the_invoice(nurse, doctor, invoice, dressing):
    assert add_line(nurse, invoice, dressing).status_code == 403
    assert add_line(doctor, invoice, dressing).status_code == 403


def test_closed_visit_blocks_desk_additions(receptionist, invoice, dressing, claimed_visit):
    from apps.encounters.models import Encounter

    Encounter.objects.filter(pk=claimed_visit.pk).update(status="closed")
    response = add_line(receptionist, invoice, dressing)
    assert response.status_code == 409
    assert "closed" in response.json()["detail"]


# --- discounts ---


def test_admin_applies_discount_with_structured_reason(admin, receptionist, invoice, dressing):
    add_line(receptionist, invoice, dressing)
    response = add_discount(admin, invoice, "1.50")
    assert response.status_code == 201, response.content
    line = response.json()
    assert line["item_type"] == "discount"
    assert line["unit_price"] == "-1.50"
    assert line["discount_reason"] == "Staff courtesy"
    assert "Staff courtesy" in line["description"]
    assert invoice.total == Decimal("2.50")

    loud = [
        entry for entry in AuditLog.objects.filter(model_label="billing.InvoiceItem")
        if "discount_applied" in entry.changes
    ]
    assert loud, "explicit discount audit entry missing"
    assert loud[-1].changes["reason"] == "Staff courtesy"


def test_discount_needs_the_named_permission(cashier, receptionist, invoice, dressing):
    """Cashier is seeded with reverse_payment but NOT apply_discount."""
    add_line(receptionist, invoice, dressing)
    response = add_discount(cashier, invoice, "1.00")
    assert response.status_code == 403


def test_discount_requires_a_reason(admin, receptionist, invoice, dressing):
    add_line(receptionist, invoice, dressing)
    response = add_discount(admin, invoice, "1.00", reason="  ")
    assert response.status_code == 400
    assert "reason" in response.json()["detail"]


def test_discount_requires_an_amount(admin, invoice):
    response = admin.post(
        items_url(invoice), {"item_type": "discount", "reason": "x"}, format="json"
    )
    assert response.status_code == 400


def test_discount_cannot_exceed_invoice_total(admin, receptionist, invoice, dressing):
    add_line(receptionist, invoice, dressing)  # total 4.00
    response = add_discount(admin, invoice, "4.50")
    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"]


def test_discount_cannot_undercut_what_is_already_paid(
    admin, cashier, receptionist, invoice, dressing
):
    from .conftest import payments_url

    add_line(receptionist, invoice, dressing)  # total 4.00
    paid = cashier.post(payments_url(invoice), {"amount": "3.00", "method": "cash"}, format="json")
    assert paid.status_code == 201, paid.content
    response = add_discount(admin, invoice, "2.00")  # would leave total 2.00 < paid 3.00
    assert response.status_code == 400
    assert "already been paid" in response.json()["detail"]


# --- voiding desk lines ---


def test_only_admin_voids_a_line_and_reason_is_required(
    admin, cashier, receptionist, invoice, dressing
):
    line_id = add_line(receptionist, invoice, dressing).json()["id"]

    denied = cashier.post(void_url(invoice, line_id), {"reason": "x"}, format="json")
    assert denied.status_code == 403
    assert admin.post(void_url(invoice, line_id), {}, format="json").status_code == 400

    response = admin.post(
        void_url(invoice, line_id), {"reason": "Added in error"}, format="json"
    )
    assert response.status_code == 200
    assert invoice.total == Decimal("0.00")
    voided = InvoiceItem.all_objects.get(pk=line_id)
    assert voided.is_voided and "Added in error" in voided.void_reason


def test_double_void_is_a_conflict(admin, receptionist, invoice, dressing):
    line_id = add_line(receptionist, invoice, dressing).json()["id"]
    assert admin.post(void_url(invoice, line_id), {"reason": "a"}, format="json").status_code == 200
    assert admin.post(void_url(invoice, line_id), {"reason": "b"}, format="json").status_code == 409


def test_void_below_paid_total_is_rejected(admin, cashier, receptionist, invoice, dressing):
    from .conftest import payments_url

    line_id = add_line(receptionist, invoice, dressing).json()["id"]
    cashier.post(payments_url(invoice), {"amount": "4.00", "method": "cash"}, format="json")
    response = admin.post(void_url(invoice, line_id), {"reason": "oops"}, format="json")
    assert response.status_code == 400
    assert "reverse a payment first" in response.json()["detail"]


def test_lab_lines_cannot_be_voided_directly(admin, doctor, draft, invoice, malaria_test):
    ordered = doctor.post(
        f"/api/v1/consultations/{draft['id']}/lab-orders/",
        {"service_items": [malaria_test.pk]},
        format="json",
    )
    assert ordered.status_code == 201, ordered.content
    line = InvoiceItem.objects.get(lab_order_id=ordered.json()["id"])
    response = admin.post(void_url(invoice, line.pk), {"reason": "x"}, format="json")
    assert response.status_code == 400
    assert "cancelling the lab order" in response.json()["detail"]
