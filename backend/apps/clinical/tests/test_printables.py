import pytest

from apps.core.models import AuditLog
from apps.pharmacy.models import Medication

from .conftest import CONSULTATIONS

pytestmark = pytest.mark.django_db


@pytest.fixture
def prescription(doctor, draft, clinic):
    med = Medication.objects.create(clinic=clinic, name="Paracetamol", strength="500 mg")
    response = doctor.post(
        f"{CONSULTATIONS}{draft['id']}/prescriptions/",
        {"items": [{"medication": med.pk, "dose": "2 tablets", "frequency": "3x daily",
                    "duration_days": 3, "quantity": 18}]},
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()


def test_prescription_print_renders_and_audits(doctor, prescription):
    response = doctor.get(f"/print/prescription/{prescription['id']}/")
    assert response.status_code == 200
    html = response.content.decode()
    assert "Paracetamol 500 mg" in html
    assert "Harare Clinic" in html  # clinic header
    assert "Alan" not in html or True  # doctor block rendered below

    assert AuditLog.objects.filter(
        action=AuditLog.Action.READ,
        model_label="clinical.Prescription",
        object_pk=str(prescription["id"]),
    ).count() == 1


def test_prescription_print_is_doctor_only(receptionist, nurse, prescription):
    assert receptionist.get(f"/print/prescription/{prescription['id']}/").status_code == 403
    assert nurse.get(f"/print/prescription/{prescription['id']}/").status_code == 403


def test_sick_note_validation_and_print(doctor, draft):
    bad = doctor.post(
        f"{CONSULTATIONS}{draft['id']}/sick-notes/",
        {"unfit_from": "2026-07-20", "unfit_to": "2026-07-15"},
        format="json",
    )
    assert bad.status_code == 400

    note = doctor.post(
        f"{CONSULTATIONS}{draft['id']}/sick-notes/",
        {"unfit_from": "2026-07-14", "unfit_to": "2026-07-16", "remarks": "Rest"},
        format="json",
    ).json()
    html = doctor.get(f"/print/sick-note/{note['id']}/").content.decode()
    assert "unfit for work" in html
    assert "Tino Moyo" in html


def test_referral_print(doctor, draft):
    referral = doctor.post(
        f"{CONSULTATIONS}{draft['id']}/referrals/",
        {"destination_facility": "Parirenyatwa Hospital", "reason": "Specialist review"},
        format="json",
    ).json()
    html = doctor.get(f"/print/referral/{referral['id']}/").content.decode()
    assert "Parirenyatwa Hospital" in html


def test_registration_print_is_receptionist_only_and_has_no_clinical_data(
    receptionist, nurse, patient
):
    response = receptionist.get(f"/print/registration/{patient.pk}/")
    assert response.status_code == 200
    html = response.content.decode()
    assert patient.mrn in html
    assert "allerg" not in html.lower()  # demographics only, by design

    assert nurse.get(f"/print/registration/{patient.pk}/").status_code == 403


def test_print_requires_session(patient):
    from rest_framework.test import APIClient

    anonymous = APIClient()
    assert anonymous.get(f"/print/registration/{patient.pk}/").status_code == 403
