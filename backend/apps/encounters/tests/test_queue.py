import datetime

import pytest

from apps.core.models import AuditLog
from apps.patients.services import register_patient

from .conftest import ENCOUNTERS

pytestmark = pytest.mark.django_db


@pytest.fixture
def second_patient(clinic, rec_user):
    return register_patient(
        clinic=clinic,
        registered_by=rec_user,
        first_name="Rudo",
        last_name="Ncube",
        date_of_birth=datetime.date(1985, 2, 2),
        sex="F",
    )


def test_emergency_jumps_the_queue(
    pay_after_clinic, open_visit, second_patient, nurse
):
    walk_in = open_visit()
    emergency = open_visit(type="emergency", patient_id=second_patient.pk)

    queue = nurse.get(f"{ENCOUNTERS}queue/").json()
    assert [v["id"] for v in queue] == [emergency["id"], walk_in["id"]]


def test_queue_filters_by_status(pay_after_clinic, open_visit, second_patient, nurse):
    from .conftest import move

    first = open_visit()
    open_visit(patient_id=second_patient.pk)
    move(nurse, first["id"], "in_triage")

    waiting = nurse.get(f"{ENCOUNTERS}queue/?status=waiting").json()
    in_triage = nurse.get(f"{ENCOUNTERS}queue/?status=in_triage").json()
    assert len(waiting) == 1
    assert [v["id"] for v in in_triage] == [first["id"]]


def test_queue_is_clinic_scoped(pay_after_clinic, open_visit, other_clinic, nurse):
    open_visit()
    queue = nurse.get(f"{ENCOUNTERS}queue/").json()
    assert len(queue) == 1  # other_clinic exists but its (empty) queue is irrelevant


def test_timeline_lists_visits_and_audits_the_read(
    pay_after_clinic, open_visit, patient, nurse, receptionist
):
    visit = open_visit()

    response = nurse.get(f"/api/v1/patients/{patient.pk}/timeline/")
    assert response.status_code == 200
    assert [v["id"] for v in response.json()] == [visit["id"]]

    read_entries = AuditLog.objects.filter(
        action=AuditLog.Action.READ,
        model_label="patients.Patient",
        object_pk=str(patient.pk),
    )
    assert read_entries.count() == 1

    # Receptionist has no clinical-history access
    assert receptionist.get(f"/api/v1/patients/{patient.pk}/timeline/").status_code == 403
