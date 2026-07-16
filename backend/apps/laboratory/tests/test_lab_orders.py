import pytest
from django.utils import timezone

from apps.billing.models import InvoiceItem, ServiceItem, ServicePrice

pytestmark = pytest.mark.django_db


@pytest.fixture
def malaria_test(clinic):
    service = ServiceItem.objects.create(
        clinic=clinic, code="lab-malaria-rdt", name="Malaria RDT", type=ServiceItem.Type.LAB
    )
    ServicePrice.objects.create(
        clinic=clinic, service=service, price="5.00", effective_from=timezone.localdate()
    )
    return service


@pytest.fixture
def unpriced_xray(clinic):
    return ServiceItem.objects.create(
        clinic=clinic, code="img-xray-chest", name="Chest X-ray", type=ServiceItem.Type.IMAGING
    )


def order_url(consultation_id):
    return f"/api/v1/consultations/{consultation_id}/lab-orders/"


def test_order_requires_lab_or_imaging_service(doctor, draft, clinic):
    consult_service = ServiceItem.objects.create(
        clinic=clinic, code="consult-x", name="Consult", type=ServiceItem.Type.CONSULTATION
    )
    response = doctor.post(
        order_url(draft["id"]), {"service_items": [consult_service.pk]}, format="json"
    )
    assert response.status_code == 400
    assert "not a lab or imaging" in str(response.json())


def test_unpriced_service_blocks_ordering(doctor, draft, unpriced_xray):
    response = doctor.post(
        order_url(draft["id"]), {"service_items": [unpriced_xray.pk]}, format="json"
    )
    assert response.status_code == 400
    assert "no price" in str(response.json())


def test_duplicate_service_in_one_order_is_rejected(doctor, draft, malaria_test):
    response = doctor.post(
        order_url(draft["id"]),
        {"service_items": [malaria_test.pk, malaria_test.pk]},
        format="json",
    )
    assert response.status_code == 400
    assert "more than once" in str(response.json())
    assert InvoiceItem.objects.count() == 0  # nothing billed


def test_only_author_orders(second_doctor, draft, malaria_test):
    response = second_doctor.post(
        order_url(draft["id"]), {"service_items": [malaria_test.pk]}, format="json"
    )
    assert response.status_code == 403


def test_order_snapshots_price_and_bills_the_invoice(doctor, draft, malaria_test, claimed_visit):
    response = doctor.post(
        order_url(draft["id"]),
        {"service_items": [malaria_test.pk], "instructions": "Fever 3 days"},
        format="json",
    )
    assert response.status_code == 201, response.content
    order = response.json()
    assert order["items"][0]["price"] == "5.00"

    line = InvoiceItem.objects.get(lab_order_id=order["id"])
    assert line.unit_price == 5
    assert line.invoice.encounter_id == claimed_visit.pk

    # Later price change must not touch the ordered snapshot or the line
    ServicePrice.objects.create(
        clinic=malaria_test.clinic, service=malaria_test, price="9.00",
        effective_from=timezone.localdate() + timezone.timedelta(days=1),
    )
    assert InvoiceItem.objects.get(lab_order_id=order["id"]).unit_price == 5


def test_cancel_voids_invoice_lines_with_reason(doctor, draft, malaria_test):
    order = doctor.post(
        order_url(draft["id"]), {"service_items": [malaria_test.pk]}, format="json"
    ).json()

    no_reason = doctor.post(f"/api/v1/lab-orders/{order['id']}/cancel/", {}, format="json")
    assert no_reason.status_code == 400

    response = doctor.post(
        f"/api/v1/lab-orders/{order['id']}/cancel/",
        {"reason": "Patient declined test"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    assert InvoiceItem.objects.filter(lab_order_id=order["id"]).count() == 0  # voided
    voided = InvoiceItem.all_objects.get(lab_order_id=order["id"])
    assert "Patient declined test" in voided.void_reason

    # Second cancel conflicts
    again = doctor.post(
        f"/api/v1/lab-orders/{order['id']}/cancel/", {"reason": "again"}, format="json"
    )
    assert again.status_code == 409


def test_lab_tech_can_view_but_not_order_or_cancel(
    user_factory, login, clinic, doctor, draft, malaria_test
):
    from apps.accounts import roles

    order = doctor.post(
        order_url(draft["id"]), {"service_items": [malaria_test.pk]}, format="json"
    ).json()
    tech = login(user_factory("lab.tendai", roles.LAB_TECHNICIAN, clinic=clinic))

    assert tech.get(f"/api/v1/lab-orders/{order['id']}/").status_code == 200
    assert tech.post(
        order_url(draft["id"]), {"service_items": [malaria_test.pk]}, format="json"
    ).status_code == 403
    assert tech.post(
        f"/api/v1/lab-orders/{order['id']}/cancel/", {"reason": "x"}, format="json"
    ).status_code == 403
