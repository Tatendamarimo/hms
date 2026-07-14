import datetime

import pytest
from django.utils import timezone

from apps.accounts import roles
from apps.billing.models import ServiceItem, ServicePrice
from apps.patients.services import register_patient

ENCOUNTERS = "/api/v1/encounters/"


@pytest.fixture
def pay_after_clinic(clinic):
    """Most flow tests don't want the payment gate in the way."""
    clinic.settings = {"payment_before_consultation": False}
    clinic.save()
    return clinic


@pytest.fixture
def rec_user(user_factory, clinic):
    return user_factory("rec.rudo", roles.RECEPTIONIST, clinic=clinic)


@pytest.fixture
def receptionist(login, rec_user):
    return login(rec_user)


@pytest.fixture
def nurse(user_factory, login, clinic):
    return login(user_factory("nurse.chipo", roles.NURSE, clinic=clinic))


@pytest.fixture
def doctor_user(user_factory, clinic):
    return user_factory("dr.alan", roles.DOCTOR, clinic=clinic)


@pytest.fixture
def doctor(login, doctor_user):
    return login(doctor_user)


@pytest.fixture
def second_doctor(user_factory, login, clinic):
    return login(user_factory("dr.busi", roles.DOCTOR, clinic=clinic))


@pytest.fixture
def cashier(user_factory, login, clinic):
    return login(user_factory("cash.tafadzwa", roles.CASHIER, clinic=clinic))


@pytest.fixture
def patient(clinic, rec_user):
    return register_patient(
        clinic=clinic,
        registered_by=rec_user,
        first_name="Tino",
        last_name="Moyo",
        date_of_birth=datetime.date(1990, 5, 1),
        sex="M",
    )


@pytest.fixture
def consult_service(clinic):
    service = ServiceItem.objects.create(
        clinic=clinic,
        code="consult-general",
        name="General Consultation",
        type=ServiceItem.Type.CONSULTATION,
    )
    ServicePrice.objects.create(
        clinic=clinic, service=service, price="10.00", effective_from=timezone.localdate()
    )
    return service


@pytest.fixture
def open_visit(receptionist, patient):
    """Check a patient in (clinic must be pay-after, or pass a service)."""

    def _open(service=None, type="walk_in", patient_id=None):
        payload = {"patient": patient_id or patient.pk, "type": type}
        if service is not None:
            payload["checkin_service"] = service.pk
        response = receptionist.post(ENCOUNTERS, payload, format="json")
        assert response.status_code == 201, response.content
        return response.json()

    return _open


def move(client, encounter_id, to, reason=""):
    return client.post(
        f"{ENCOUNTERS}{encounter_id}/transition/", {"to": to, "reason": reason}, format="json"
    )
