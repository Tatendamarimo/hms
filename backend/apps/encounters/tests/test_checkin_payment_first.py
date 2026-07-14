"""The pilot clinic's primary flow (decision Q2): fee at check-in, nothing
proceeds until the invoice is settled."""

import pytest

from apps.billing.models import Invoice

from .conftest import ENCOUNTERS, move

pytestmark = pytest.mark.django_db


def test_checkin_requires_consultation_service(receptionist, patient, clinic):
    response = receptionist.post(ENCOUNTERS, {"patient": patient.pk}, format="json")
    assert response.status_code == 400
    assert "checkin_service" in response.json()


def test_checkin_creates_invoice_with_fee_line(open_visit, consult_service):
    visit = open_visit(service=consult_service)

    invoice = visit["invoice"]
    assert invoice["number"] == "INV-HARARE-2026-000001"
    assert invoice["total"] == "10.00"
    assert invoice["status"] == "unpaid"


def test_triage_blocked_until_paid_then_allowed(
    open_visit, consult_service, receptionist, nurse
):
    visit = open_visit(service=consult_service)

    blocked = move(nurse, visit["id"], "in_triage")
    assert blocked.status_code == 400
    assert "settled" in blocked.json()["detail"]

    invoice_id = visit["invoice"]["id"]
    paid = receptionist.post(
        f"/api/v1/billing/invoices/{invoice_id}/payments/",
        {"amount": "10.00", "method": "ecocash", "reference": "MP12345"},
        format="json",
    )
    assert paid.status_code == 201
    assert paid.json()["receipt_number"] == "REC-HARARE-2026-000001"

    assert move(nurse, visit["id"], "in_triage").status_code == 200


def test_partial_payment_does_not_open_the_gate(
    open_visit, consult_service, receptionist, nurse
):
    visit = open_visit(service=consult_service)
    invoice_id = visit["invoice"]["id"]
    payments_url = f"/api/v1/billing/invoices/{invoice_id}/payments/"

    receptionist.post(payments_url, {"amount": "4.00", "method": "cash"}, format="json")
    invoice = receptionist.get(f"/api/v1/billing/invoices/{invoice_id}/").json()
    assert invoice["status"] == "part_paid"
    assert invoice["balance"] == "6.00"

    assert move(nurse, visit["id"], "in_triage").status_code == 400

    receptionist.post(payments_url, {"amount": "6.00", "method": "cash"}, format="json")
    assert move(nurse, visit["id"], "in_triage").status_code == 200


def test_overpayment_is_rejected(open_visit, consult_service, receptionist):
    visit = open_visit(service=consult_service)
    response = receptionist.post(
        f"/api/v1/billing/invoices/{visit['invoice']['id']}/payments/",
        {"amount": "50.00", "method": "cash"},
        format="json",
    )
    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"]


def test_service_without_price_blocks_checkin(receptionist, patient, clinic):
    from apps.billing.models import ServiceItem

    unpriced = ServiceItem.objects.create(
        clinic=clinic, code="consult-x", name="X", type=ServiceItem.Type.CONSULTATION
    )
    response = receptionist.post(
        ENCOUNTERS,
        {"patient": patient.pk, "checkin_service": unpriced.pk},
        format="json",
    )
    assert response.status_code == 400
    assert Invoice.all_objects.count() == 0  # nothing half-created


def test_patient_cannot_have_two_open_visits(
    open_visit, consult_service, patient, receptionist
):
    open_visit(service=consult_service)
    response = receptionist.post(
        ENCOUNTERS,
        {"patient": patient.pk, "checkin_service": consult_service.pk},
        format="json",
    )
    assert response.status_code == 400
    assert "open visit" in str(response.json())
