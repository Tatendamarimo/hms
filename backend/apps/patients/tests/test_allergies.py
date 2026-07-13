import pytest

pytestmark = pytest.mark.django_db

PATIENTS = "/api/v1/patients/"


@pytest.fixture
def allergy(nurse, registered_patient):
    response = nurse.post(
        f"{PATIENTS}{registered_patient['id']}/allergies/",
        {"substance": "Penicillin", "reaction": "Rash", "severity": "severe"},
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()


def test_allergy_appears_in_summary_banner(nurse, registered_patient, allergy):
    summary = nurse.get(f"{PATIENTS}{registered_patient['id']}/summary/").json()
    assert [a["substance"] for a in summary["allergies"]] == ["Penicillin"]


def test_void_requires_reason(nurse, registered_patient, allergy):
    url = f"{PATIENTS}{registered_patient['id']}/allergies/{allergy['id']}/void/"
    assert nurse.post(url, {"reason": ""}, format="json").status_code == 400

    assert nurse.post(url, {"reason": "Entered on wrong patient"}, format="json").status_code == 204
    summary = nurse.get(f"{PATIENTS}{registered_patient['id']}/summary/").json()
    assert summary["allergies"] == []


def test_receptionist_cannot_touch_allergies(receptionist, registered_patient):
    url = f"{PATIENTS}{registered_patient['id']}/allergies/"
    assert receptionist.get(url).status_code == 403
    assert (
        receptionist.post(url, {"substance": "X", "severity": "mild"}, format="json").status_code
        == 403
    )


def test_conditions_add_and_void(nurse, registered_patient):
    url = f"{PATIENTS}{registered_patient['id']}/conditions/"
    created = nurse.post(url, {"condition": "Hypertension"}, format="json")
    assert created.status_code == 201

    summary = nurse.get(f"{PATIENTS}{registered_patient['id']}/summary/").json()
    assert [c["condition"] for c in summary["conditions"]] == ["Hypertension"]

    void = nurse.post(
        f"{url}{created.json()['id']}/void/", {"reason": "duplicate entry"}, format="json"
    )
    assert void.status_code == 204
