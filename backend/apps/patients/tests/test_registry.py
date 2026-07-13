import pytest

from apps.core.models import AuditLog
from apps.patients.models import Patient

pytestmark = pytest.mark.django_db

PATIENTS = "/api/v1/patients/"


def test_registration_issues_sequential_mrns(receptionist, patient_payload):
    first = receptionist.post(PATIENTS, patient_payload, format="json").json()
    second_payload = {
        **patient_payload, "first_name": "Rudo", "national_id": "", "phone": "",
    }
    second = receptionist.post(PATIENTS, second_payload, format="json").json()

    assert first["mrn"] == "HARARE-000001"
    assert second["mrn"] == "HARARE-000002"


def test_registration_requires_consent(receptionist, patient_payload):
    del patient_payload["consent_confirmed"]
    assert receptionist.post(PATIENTS, patient_payload, format="json").status_code == 400

    patient_payload["consent_confirmed"] = False
    response = receptionist.post(PATIENTS, patient_payload, format="json")
    assert response.status_code == 400
    assert Patient.objects.count() == 0


def test_consent_is_stamped_on_registration(registered_patient):
    patient = Patient.objects.get(pk=registered_patient["id"])
    assert patient.consent_given_at is not None
    assert patient.consent_captured_by.username == "rec.rudo"


def test_duplicate_national_id_returns_409_with_candidates(
    receptionist, registered_patient, patient_payload
):
    payload = {**patient_payload, "first_name": "Other", "phone": ""}
    response = receptionist.post(PATIENTS, payload, format="json")

    assert response.status_code == 409
    candidates = response.json()["candidates"]
    assert [c["mrn"] for c in candidates] == [registered_patient["mrn"]]
    assert Patient.objects.count() == 1


def test_duplicate_override_creates_and_audits(
    receptionist, registered_patient, patient_payload
):
    payload = {**patient_payload, "first_name": "Other", "create_anyway": True}
    response = receptionist.post(PATIENTS, payload, format="json")

    assert response.status_code == 201
    assert Patient.objects.count() == 2

    override_entries = AuditLog.objects.filter(
        model_label="patients.Patient",
        changes__has_key="duplicate_override",
    )
    assert override_entries.count() == 1
    assert override_entries.get().changes["duplicate_override"] == [registered_patient["id"]]


def test_search_finds_by_name_phone_and_mrn(receptionist, registered_patient):
    for query in ["Marimo", "+26377", "HARARE-000001", "63-123456A70"]:
        results = receptionist.get(f"{PATIENTS}search/?q={query}").json()
        assert [p["id"] for p in results] == [registered_patient["id"]], query

    assert receptionist.get(f"{PATIENTS}search/?q=zz").json() == []
    assert receptionist.get(f"{PATIENTS}search/?q=a").json() == []  # too short


def test_mrn_is_immutable_via_api(receptionist, registered_patient):
    response = receptionist.patch(
        f"{PATIENTS}{registered_patient['id']}/", {"mrn": "HACKED-1"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["mrn"] == "HARARE-000001"


def test_role_boundaries(nurse, cashier, registered_patient, patient_payload):
    # Nurse cannot register patients
    assert nurse.post(PATIENTS, patient_payload, format="json").status_code == 403
    # Cashier can search (needed for billing) but cannot see the clinical summary
    assert cashier.get(f"{PATIENTS}search/?q=Marimo").status_code == 200
    assert cashier.get(f"{PATIENTS}{registered_patient['id']}/summary/").status_code == 403
    # Nurse can see the clinical summary
    assert nurse.get(f"{PATIENTS}{registered_patient['id']}/summary/").status_code == 200
