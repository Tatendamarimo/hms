"""Slice 8: per-patient unpaid balances view (FRD §5.7)."""

import datetime

import pytest

from apps.billing import services
from apps.billing.models import InvoiceItem
from apps.encounters.models import Encounter
from apps.patients.services import register_patient

from .conftest import items_url, payments_url, reverse_url

pytestmark = pytest.mark.django_db

UNPAID = "/api/v1/billing/unpaid/"


def add_line(client, invoice, service, quantity=1):
    response = client.post(
        items_url(invoice),
        {"service_item": service.pk, "quantity": quantity},
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()


def pay(client, invoice, amount):
    response = client.post(
        payments_url(invoice), {"amount": amount, "method": "cash"}, format="json"
    )
    assert response.status_code == 201, response.content
    return response.json()


def results(client):
    response = client.get(UNPAID)
    assert response.status_code == 200, response.content
    return response.json()["results"]


# --- edges first ---


def test_unpaid_view_roles(cashier, admin, receptionist, nurse, doctor):
    assert cashier.get(UNPAID).status_code == 200
    assert admin.get(UNPAID).status_code == 200
    for client in (receptionist, nurse, doctor):
        assert client.get(UNPAID).status_code == 403


def test_empty_invoice_is_not_a_debt(cashier, invoice):
    assert results(cashier) == []


def test_paid_invoice_is_excluded(cashier, receptionist, invoice, dressing):
    add_line(receptionist, invoice, dressing)
    pay(cashier, invoice, "4.00")
    assert results(cashier) == []


def test_voided_line_carries_no_debt(admin, receptionist, invoice, dressing):
    line = add_line(receptionist, invoice, dressing)
    voided = admin.post(
        f"{items_url(invoice)}{line['id']}/void/", {"reason": "entry error"},
        format="json",
    )
    assert voided.status_code == 200, voided.content
    assert results(admin) == []


# --- outstanding balances ---


def test_part_paid_invoice_is_listed_per_patient(
    cashier, receptionist, invoice, dressing, patient
):
    add_line(receptionist, invoice, dressing)
    pay(cashier, invoice, "1.00")

    entries = results(cashier)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["patient"] == {
        "id": patient.pk, "mrn": patient.mrn, "full_name": "Tino Moyo",
    }
    assert entry["outstanding"] == "3.00"
    row = entry["invoices"][0]
    assert row["number"] == invoice.number
    assert row["total"] == "4.00"
    assert row["paid"] == "1.00"
    assert row["outstanding"] == "3.00"
    assert row["encounter_status"] == "in_consultation"


def test_discount_reduces_the_outstanding_balance(
    admin, receptionist, invoice, dressing
):
    add_line(receptionist, invoice, dressing)
    discounted = admin.post(
        items_url(invoice),
        {"item_type": "discount", "amount": "1.50", "reason": "Staff courtesy"},
        format="json",
    )
    assert discounted.status_code == 201, discounted.content
    assert results(admin)[0]["outstanding"] == "2.50"


def test_reversal_puts_the_invoice_back_on_the_list(
    cashier, receptionist, invoice, dressing
):
    add_line(receptionist, invoice, dressing)
    payment = pay(cashier, invoice, "4.00")
    assert results(cashier) == []

    reversed_ = cashier.post(
        reverse_url(payment["id"]), {"reason": "wrong invoice"}, format="json"
    )
    assert reversed_.status_code == 201, reversed_.content
    assert results(cashier)[0]["outstanding"] == "4.00"


def test_balances_aggregate_across_a_patients_visits(
    cashier, receptionist, rec_user, invoice, dressing, patient, claimed_visit
):
    """The main use case: debt carried out of a closed visit plus a new one."""
    add_line(receptionist, invoice, dressing)
    pay(cashier, invoice, "1.00")  # 3.00 left behind
    Encounter.objects.filter(pk=claimed_visit.pk).update(status="closed")

    second = receptionist.post(
        "/api/v1/encounters/", {"patient": patient.pk}, format="json"
    )
    assert second.status_code == 201, second.content
    second_visit = Encounter.objects.get(pk=second.json()["id"])
    second_invoice = services.ensure_invoice(second_visit, created_by=rec_user)
    add_line(receptionist, second_invoice, dressing)  # 4.00 owing

    entries = results(cashier)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["outstanding"] == "7.00"
    assert [row["outstanding"] for row in entry["invoices"]] == ["4.00", "3.00"]
    statuses = {row["encounter_status"] for row in entry["invoices"]}
    assert statuses == {"closed", "waiting"}


def test_patients_owing_most_come_first(
    cashier, receptionist, rec_user, clinic, invoice, dressing
):
    add_line(receptionist, invoice, dressing)  # Tino owes 4.00

    debtor = register_patient(
        clinic=clinic, registered_by=rec_user,
        first_name="Rudo", last_name="Ncube",
        date_of_birth=datetime.date(1985, 2, 2), sex="F",
    )
    checked_in = receptionist.post(
        "/api/v1/encounters/", {"patient": debtor.pk}, format="json"
    )
    assert checked_in.status_code == 201, checked_in.content
    visit = Encounter.objects.get(pk=checked_in.json()["id"])
    second_invoice = services.ensure_invoice(visit, created_by=rec_user)
    add_line(receptionist, second_invoice, dressing, quantity=3)  # Rudo owes 12.00

    entries = results(cashier)
    assert [e["patient"]["full_name"] for e in entries] == ["Rudo Ncube", "Tino Moyo"]
    assert [e["outstanding"] for e in entries] == ["12.00", "4.00"]


def test_foreign_clinic_debt_is_invisible(
    cashier, rec_user, other_clinic, invoice, receptionist, dressing
):
    add_line(receptionist, invoice, dressing)

    stranger = register_patient(
        clinic=other_clinic, registered_by=rec_user,
        first_name="Far", last_name="Away",
        date_of_birth=datetime.date(1970, 1, 1), sex="M",
    )
    foreign_visit = Encounter.objects.create(
        clinic=other_clinic, patient=stranger,
        type=Encounter.Type.WALK_IN, status=Encounter.Status.WAITING,
        created_by=rec_user,
    )
    foreign_invoice = services.ensure_invoice(foreign_visit, created_by=rec_user)
    InvoiceItem.objects.create(
        clinic=other_clinic, invoice=foreign_invoice,
        description="Foreign consult", quantity=1, unit_price="9.00",
        created_by=rec_user,
    )

    entries = results(cashier)
    assert [e["patient"]["full_name"] for e in entries] == ["Tino Moyo"]
