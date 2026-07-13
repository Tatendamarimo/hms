import pytest

from apps.accounts import roles


@pytest.fixture
def receptionist(user_factory, login, clinic):
    return login(user_factory("rec.rudo", roles.RECEPTIONIST, clinic=clinic))


@pytest.fixture
def nurse(user_factory, login, clinic):
    return login(user_factory("nurse.chipo", roles.NURSE, clinic=clinic))


@pytest.fixture
def cashier(user_factory, login, clinic):
    return login(user_factory("cash.tafadzwa", roles.CASHIER, clinic=clinic))


VALID_PATIENT = {
    "first_name": "Tatenda",
    "last_name": "Marimo",
    "date_of_birth": "1998-04-12",
    "sex": "M",
    "national_id": "63-123456A70",
    "phone": "+263771234567",
    "consent_confirmed": True,
}


@pytest.fixture
def patient_payload():
    return dict(VALID_PATIENT)


@pytest.fixture
def registered_patient(receptionist, patient_payload):
    response = receptionist.post("/api/v1/patients/", patient_payload, format="json")
    assert response.status_code == 201, response.content
    return response.json()
