import pytest

from apps.core.models import AuditLog
from apps.encounters.models import Encounter, Vitals

from .conftest import ENCOUNTERS, move

pytestmark = pytest.mark.django_db

NORMAL = {"systolic": 120, "diastolic": 80, "pulse": 72, "temperature": "36.6"}


def vitals_url(visit_id):
    return f"{ENCOUNTERS}{visit_id}/vitals/"


@pytest.fixture
def triaged_visit(pay_after_clinic, open_visit, nurse):
    visit = open_visit()
    assert move(nurse, visit["id"], "in_triage").status_code == 200
    return visit


# --- Edge cases first ---


def test_vitals_rejected_before_triage_starts(pay_after_clinic, open_visit, nurse):
    visit = open_visit()  # status: waiting
    response = nurse.post(vitals_url(visit["id"]), NORMAL, format="json")
    assert response.status_code == 400
    assert "triage" in str(response.json()).lower()
    assert Vitals.objects.count() == 0


def test_vitals_rejected_on_closed_visit(triaged_visit, nurse, receptionist):
    move(nurse, triaged_visit["id"], "awaiting_doctor")
    # Patient walks out; visit is closed as LWBS
    Encounter.objects.filter(pk=triaged_visit["id"]).update(status="left_without_being_seen")
    response = nurse.post(vitals_url(triaged_visit["id"]), NORMAL, format="json")
    assert response.status_code == 400


def test_implausible_values_are_rejected_not_flagged(triaged_visit, nurse):
    for bad in [
        {**NORMAL, "systolic": 500},
        {**NORMAL, "spo2": 120},
        {**NORMAL, "temperature": "10.0"},
        {**NORMAL, "pulse": 5},
    ]:
        response = nurse.post(vitals_url(triaged_visit["id"]), bad, format="json")
        assert response.status_code == 400, bad
    assert Vitals.objects.count() == 0
    # Rejection means no auto-transition either
    assert Encounter.objects.get(pk=triaged_visit["id"]).status == "in_triage"


def test_permissions_on_vitals_endpoints(triaged_visit, receptionist, doctor, nurse):
    url = vitals_url(triaged_visit["id"])
    # Receptionist: no clinical access at all
    assert receptionist.get(url).status_code == 403
    assert receptionist.post(url, NORMAL, format="json").status_code == 403
    # Doctor: may read, may not record
    assert doctor.get(url).status_code == 200
    assert doctor.post(url, NORMAL, format="json").status_code == 403
    # Nurse: records
    assert nurse.post(url, NORMAL, format="json").status_code == 201


def test_void_requires_reason_and_hides_record(triaged_visit, nurse):
    created = nurse.post(vitals_url(triaged_visit["id"]), NORMAL, format="json").json()
    void_url = f"{ENCOUNTERS}{triaged_visit['id']}/vitals/{created['id']}/void/"

    assert nurse.post(void_url, {"reason": ""}, format="json").status_code == 400
    assert nurse.post(void_url, {"reason": "wrong patient"}, format="json").status_code == 204
    assert nurse.get(vitals_url(triaged_visit["id"])).json() == []
    assert Vitals.all_objects.count() == 1  # soft-deleted, never gone


# --- Flagging ---


def test_abnormal_values_are_flagged_with_direction(triaged_visit, nurse):
    response = nurse.post(
        vitals_url(triaged_visit["id"]),
        {"systolic": 190, "diastolic": 120, "pulse": 40, "temperature": "36.6"},
        format="json",
    )
    flags = {f["field"]: f["direction"] for f in response.json()["flags"]}
    assert flags == {"systolic": "high", "diastolic": "high", "pulse": "low"}


def test_normal_values_produce_no_flags(triaged_visit, nurse):
    response = nurse.post(vitals_url(triaged_visit["id"]), NORMAL, format="json")
    assert response.json()["flags"] == []


def test_clinic_can_override_reference_ranges(pay_after_clinic, open_visit, nurse):
    pay_after_clinic.settings = {
        **pay_after_clinic.settings,
        "vitals_reference_ranges": {"systolic": {"low": 100, "high": 115}},
    }
    pay_after_clinic.save()
    visit = open_visit()
    move(nurse, visit["id"], "in_triage")

    response = nurse.post(vitals_url(visit["id"]), NORMAL, format="json")
    flags = response.json()["flags"]
    assert [f["field"] for f in flags] == ["systolic"]  # 120 > custom high of 115


def test_ranges_are_snapshotted_not_live(triaged_visit, nurse, pay_after_clinic):
    """ADR-0001: changing thresholds later must not re-colour history."""
    created = nurse.post(vitals_url(triaged_visit["id"]), NORMAL, format="json").json()
    assert created["flags"] == []

    pay_after_clinic.settings = {
        **pay_after_clinic.settings,
        "vitals_reference_ranges": {"systolic": {"low": 100, "high": 110}},
    }
    pay_after_clinic.save()

    stored = nurse.get(vitals_url(triaged_visit["id"])).json()[0]
    assert stored["flags"] == []  # still normal, as seen at the time of care
    assert stored["applied_ranges"]["systolic"]["high"] == 140  # the ranges used then


# --- State machine integration ---


def test_recording_vitals_advances_triage_to_awaiting_doctor(triaged_visit, nurse):
    nurse.post(vitals_url(triaged_visit["id"]), NORMAL, format="json")
    assert Encounter.objects.get(pk=triaged_visit["id"]).status == "awaiting_doctor"


def test_second_recording_does_not_double_transition(triaged_visit, nurse):
    nurse.post(vitals_url(triaged_visit["id"]), NORMAL, format="json")
    # Doctor asks for a re-check while patient still awaits them
    response = nurse.post(
        vitals_url(triaged_visit["id"]), {**NORMAL, "pulse": 80}, format="json"
    )
    assert response.status_code == 201
    assert Encounter.objects.get(pk=triaged_visit["id"]).status == "awaiting_doctor"
    assert Vitals.objects.count() == 2


def test_vitals_allowed_during_consultation(triaged_visit, nurse, doctor):
    nurse.post(vitals_url(triaged_visit["id"]), NORMAL, format="json")
    move(doctor, triaged_visit["id"], "in_consultation")

    response = nurse.post(vitals_url(triaged_visit["id"]), NORMAL, format="json")
    assert response.status_code == 201
    assert Encounter.objects.get(pk=triaged_visit["id"]).status == "in_consultation"


# --- Audit ---


def test_vitals_reads_and_writes_are_audited(triaged_visit, nurse):
    nurse.post(vitals_url(triaged_visit["id"]), NORMAL, format="json")
    nurse.get(vitals_url(triaged_visit["id"]))

    assert AuditLog.objects.filter(
        model_label="encounters.Vitals", action=AuditLog.Action.CREATE
    ).count() == 1
    assert AuditLog.objects.filter(
        model_label="encounters.Encounter",
        action=AuditLog.Action.READ,
        object_pk=str(triaged_visit["id"]),
    ).count() == 1
