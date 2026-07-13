import datetime

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts import roles
from apps.billing.models import ServiceItem, ServicePrice

pytestmark = pytest.mark.django_db

CATALOG = "/api/v1/billing/catalog/"
PRICES = "/api/v1/billing/prices/"


@pytest.fixture
def admin_client(user_factory, login, clinic):
    return login(user_factory("admin.tino", roles.ADMIN, clinic=clinic))


@pytest.fixture
def receptionist_client(user_factory, login, clinic):
    return login(user_factory("rec.rudo", roles.RECEPTIONIST, clinic=clinic))


@pytest.fixture
def service(clinic):
    return ServiceItem.objects.create(
        clinic=clinic,
        code="consult-general",
        name="General Consultation",
        type=ServiceItem.Type.CONSULTATION,
    )


def test_current_price_uses_latest_effective_not_future(service, clinic):
    today = timezone.localdate()
    ServicePrice.objects.create(
        clinic=clinic, service=service, price="10.00",
        effective_from=today - datetime.timedelta(days=30),
    )
    ServicePrice.objects.create(
        clinic=clinic, service=service, price="12.00",
        effective_from=today - datetime.timedelta(days=1),
    )
    ServicePrice.objects.create(
        clinic=clinic, service=service, price="99.00",
        effective_from=today + datetime.timedelta(days=5),  # scheduled future price
    )
    assert str(service.current_price()) == "12.00"


def test_service_without_price_has_no_current_price(service):
    assert service.current_price() is None


def test_admin_creates_service_and_price(admin_client, service):
    response = admin_client.post(
        CATALOG,
        {"code": "proc-suturing", "name": "Suturing", "type": "procedure"},
        format="json",
    )
    assert response.status_code == 201, response.content

    response = admin_client.post(
        PRICES,
        {"service": service.pk, "price": "15.00",
         "effective_from": str(timezone.localdate())},
        format="json",
    )
    assert response.status_code == 201, response.content
    assert str(service.current_price()) == "15.00"


def test_duplicate_effective_date_rejected(admin_client, service, clinic):
    today = timezone.localdate()
    ServicePrice.objects.create(clinic=clinic, service=service, price="10.00",
                                effective_from=today)
    response = admin_client.post(
        PRICES, {"service": service.pk, "price": "11.00", "effective_from": str(today)},
        format="json",
    )
    assert response.status_code == 400


def test_receptionist_can_read_but_not_manage_catalog(receptionist_client, service):
    assert receptionist_client.get(CATALOG).status_code == 200
    response = receptionist_client.post(
        CATALOG, {"code": "x", "name": "X", "type": "other"}, format="json"
    )
    assert response.status_code == 403


def test_catalog_is_clinic_scoped(admin_client, other_clinic, service):
    ServiceItem.objects.create(
        clinic=other_clinic, code="other-svc", name="Other", type=ServiceItem.Type.OTHER
    )
    response = admin_client.get(CATALOG)
    codes = [item["code"] for item in response.json()["results"]]
    assert codes == ["consult-general"]


def test_seed_catalog_command_is_idempotent(clinic):
    call_command("seed_catalog", clinic.code)
    call_command("seed_catalog", clinic.code)
    assert ServiceItem.objects.filter(clinic=clinic).count() == 4
