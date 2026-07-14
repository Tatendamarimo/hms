import pytest
from django.core.management import call_command

from apps.clinical.models import Diagnosis

from .conftest import CONSULTATIONS

pytestmark = pytest.mark.django_db


@pytest.fixture
def icd10(db):
    call_command("seed_diagnoses")


def test_seed_is_idempotent(icd10):
    count = Diagnosis.objects.count()
    call_command("seed_diagnoses")
    assert Diagnosis.objects.count() == count
    assert count >= 40


def test_search_by_code_and_name(icd10, doctor):
    by_code = doctor.get("/api/v1/diagnoses/?q=B54").json()
    assert [d["code"] for d in by_code] == ["B54"]

    by_name = doctor.get("/api/v1/diagnoses/?q=malaria").json()
    assert {d["code"] for d in by_name} == {"B50.9", "B54"}


def test_diagnosis_picklist_is_doctor_only(icd10, nurse, receptionist):
    assert nurse.get("/api/v1/diagnoses/?q=B54").status_code == 403
    assert receptionist.get("/api/v1/diagnoses/?q=B54").status_code == 403


def test_add_coded_and_free_text_diagnoses(icd10, doctor, draft):
    malaria = Diagnosis.objects.get(code="B54")
    coded = doctor.post(
        f"{CONSULTATIONS}{draft['id']}/diagnoses/", {"diagnosis": malaria.pk}, format="json"
    )
    assert coded.status_code == 201
    assert coded.json()["code"] == "B54"

    free = doctor.post(
        f"{CONSULTATIONS}{draft['id']}/diagnoses/", {"free_text": "Suspected typhoid"},
        format="json",
    )
    assert free.status_code == 201


def test_diagnosis_requires_code_or_text(doctor, draft):
    response = doctor.post(f"{CONSULTATIONS}{draft['id']}/diagnoses/", {}, format="json")
    assert response.status_code == 400


def test_diagnosis_alone_satisfies_sign_content_rule(icd10, doctor, draft):
    malaria = Diagnosis.objects.get(code="B54")
    doctor.post(f"{CONSULTATIONS}{draft['id']}/diagnoses/", {"diagnosis": malaria.pk},
                format="json")
    assert doctor.post(f"{CONSULTATIONS}{draft['id']}/sign/").status_code == 200


def test_remove_diagnosis_draft_only_and_audited(icd10, doctor, draft, signable_draft):
    from apps.core.models import AuditLog

    added = doctor.post(
        f"{CONSULTATIONS}{draft['id']}/diagnoses/", {"free_text": "URTI"}, format="json"
    ).json()
    removed = doctor.delete(f"{CONSULTATIONS}{draft['id']}/diagnoses/{added['id']}/")
    assert removed.status_code == 204
    assert AuditLog.objects.filter(changes__has_key="removed_diagnosis").count() == 1

    # After signing, the diagnosis list is frozen
    doctor.post(f"{CONSULTATIONS}{draft['id']}/diagnoses/", {"free_text": "kept"}, format="json")
    doctor.post(f"{CONSULTATIONS}{draft['id']}/sign/")
    frozen = doctor.post(
        f"{CONSULTATIONS}{draft['id']}/diagnoses/", {"free_text": "late"}, format="json"
    )
    assert frozen.status_code == 409
