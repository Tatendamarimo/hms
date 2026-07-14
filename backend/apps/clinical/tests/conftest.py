import datetime

import pytest

from apps.accounts import roles
from apps.encounters.models import Encounter
from apps.patients.services import register_patient

CONSULTATIONS = "/api/v1/consultations/"


@pytest.fixture
def pay_after_clinic(clinic):
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
def admin(user_factory, login, clinic):
    return login(user_factory("admin.tino", roles.ADMIN, clinic=clinic))


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
def claimed_visit(pay_after_clinic, receptionist, nurse, doctor, patient):
    """An encounter in `in_consultation`, claimed by dr.alan."""
    created = receptionist.post(
        "/api/v1/encounters/", {"patient": patient.pk}, format="json"
    )
    assert created.status_code == 201, created.content
    visit_id = created.json()["id"]
    for client, target in [
        (nurse, "in_triage"), (nurse, "awaiting_doctor"), (doctor, "in_consultation"),
    ]:
        response = client.post(
            f"/api/v1/encounters/{visit_id}/transition/", {"to": target}, format="json"
        )
        assert response.status_code == 200, response.content
    return Encounter.objects.get(pk=visit_id)


@pytest.fixture
def draft(doctor, claimed_visit):
    response = doctor.post(f"/api/v1/encounters/{claimed_visit.pk}/consultation/")
    assert response.status_code == 201, response.content
    return response.json()


@pytest.fixture
def signable_draft(doctor, draft):
    response = doctor.patch(
        f"{CONSULTATIONS}{draft['id']}/",
        {"clinical_notes": "URTI, no red flags.", "treatment_plan": "Rest and fluids."},
        format="json",
    )
    assert response.status_code == 200, response.content
    return response.json()
