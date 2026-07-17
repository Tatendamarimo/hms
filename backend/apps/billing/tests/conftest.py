import pytest
from django.utils import timezone

from apps.accounts import roles
from apps.billing import services
from apps.billing.models import ServiceItem, ServicePrice
from apps.clinical.tests.conftest import *  # noqa: F401,F403 — reuse clinical fixtures


@pytest.fixture
def cashier_user(user_factory, clinic):
    return user_factory("cash.kuda", roles.CASHIER, clinic=clinic)


@pytest.fixture
def cashier(login, cashier_user):
    return login(cashier_user)


def _priced_service(clinic, code, name, type_, price):
    service = ServiceItem.objects.create(clinic=clinic, code=code, name=name, type=type_)
    ServicePrice.objects.create(
        clinic=clinic, service=service, price=price, effective_from=timezone.localdate()
    )
    return service


@pytest.fixture
def dressing(clinic):
    return _priced_service(clinic, "proc-dressing", "Wound dressing",
                           ServiceItem.Type.PROCEDURE, "4.00")


@pytest.fixture
def malaria_test(clinic):
    return _priced_service(clinic, "lab-malaria-rdt", "Malaria RDT",
                           ServiceItem.Type.LAB, "5.00")


@pytest.fixture
def invoice(claimed_visit, rec_user):
    """Empty invoice on an open (pay-after) visit in consultation."""
    return services.ensure_invoice(claimed_visit, created_by=rec_user)


def items_url(invoice):
    return f"/api/v1/billing/invoices/{invoice.pk}/items/"


def void_url(invoice, item_id):
    return f"/api/v1/billing/invoices/{invoice.pk}/items/{item_id}/void/"


def payments_url(invoice):
    return f"/api/v1/billing/invoices/{invoice.pk}/payments/"


def reverse_url(payment_id):
    return f"/api/v1/billing/payments/{payment_id}/reverse/"
