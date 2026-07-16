import pytest

from apps.core.models import AuditLog
from apps.pharmacy.models import Medication

from .conftest import CONSULTATIONS

pytestmark = pytest.mark.django_db


@pytest.fixture
def amoxicillin(clinic):
    return Medication.objects.create(
        clinic=clinic, name="Amoxicillin", strength="500 mg", form="capsule"
    )


@pytest.fixture
def penicillin_v(clinic):
    return Medication.objects.create(
        clinic=clinic, name="Penicillin V", strength="250 mg", form="tablet"
    )


def rx_payload(medication, **overrides):
    item = {
        "medication": medication.pk,
        "dose": "1 capsule",
        "frequency": "3x daily",
        "duration_days": 7,
        "quantity": 21,
        **overrides,
    }
    return {"items": [item]}


def rx_url(consultation_id):
    return f"{CONSULTATIONS}{consultation_id}/prescriptions/"


# --- Edge cases first ---


def test_prescription_requires_items(doctor, draft):
    assert doctor.post(rx_url(draft["id"]), {"items": []}, format="json").status_code == 400


def test_item_requires_medication_or_note(doctor, draft):
    payload = {"items": [{"dose": "x", "frequency": "y", "duration_days": 1, "quantity": 1}]}
    assert doctor.post(rx_url(draft["id"]), payload, format="json").status_code == 400


def test_only_author_prescribes(second_doctor, draft, amoxicillin):
    response = second_doctor.post(rx_url(draft["id"]), rx_payload(amoxicillin), format="json")
    assert response.status_code == 403


def test_nurse_cannot_prescribe(nurse, draft, amoxicillin):
    response = nurse.post(rx_url(draft["id"]), rx_payload(amoxicillin), format="json")
    assert response.status_code == 403


def test_no_prescriptions_on_closed_visits(doctor, cashier_closes_visit, amoxicillin):
    draft_id = cashier_closes_visit
    response = doctor.post(rx_url(draft_id), rx_payload(amoxicillin), format="json")
    assert response.status_code == 409


@pytest.fixture
def cashier_closes_visit(doctor, signable_draft, claimed_visit, user_factory, login, clinic):
    from apps.accounts import roles

    doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/")
    cashier = login(user_factory("cash.t", roles.CASHIER, clinic=clinic))
    response = cashier.post(
        f"/api/v1/encounters/{claimed_visit.pk}/transition/", {"to": "closed"}, format="json"
    )
    assert response.status_code == 200, response.content
    return signable_draft["id"]


# --- Allergy guard ---


@pytest.fixture
def penicillin_allergy(nurse, patient):
    response = nurse.post(
        f"/api/v1/patients/{patient.pk}/allergies/",
        {"substance": "Penicillin", "reaction": "Anaphylaxis", "severity": "severe"},
        format="json",
    )
    assert response.status_code == 201
    return response.json()


def test_allergy_match_blocks_with_409_and_details(
    doctor, draft, penicillin_v, penicillin_allergy
):
    response = doctor.post(rx_url(draft["id"]), rx_payload(penicillin_v), format="json")
    assert response.status_code == 409
    warnings = response.json()["allergy_warnings"]
    assert warnings[0]["substance"] == "Penicillin"
    assert warnings[0]["medication"] == "Penicillin V"


def test_acknowledged_override_creates_and_audits(
    doctor, draft, penicillin_v, penicillin_allergy
):
    payload = rx_payload(penicillin_v)
    payload["acknowledged_allergy_ids"] = [penicillin_allergy["id"]]
    response = doctor.post(rx_url(draft["id"]), payload, format="json")
    assert response.status_code == 201

    entry = AuditLog.objects.get(changes__has_key="allergy_acknowledged")
    assert entry.changes["allergy_acknowledged"][0]["substance"] == "Penicillin"
    assert entry.user.username == "dr.alan"


def test_unrelated_medication_passes_silently(doctor, draft, amoxicillin, penicillin_allergy):
    """Documented limitation: substring matching knows no pharmacology —
    Amoxicillin sails past a penicillin allergy (interaction engine deferred)."""
    response = doctor.post(rx_url(draft["id"]), rx_payload(amoxicillin), format="json")
    assert response.status_code == 201
    assert response.json()["items"][0]["display_name"] == "Amoxicillin 500 mg (capsule)"


def test_free_text_items_are_also_guarded(doctor, draft, penicillin_allergy):
    payload = {"items": [{
        "medication_note": "Penicillin injection stat",
        "dose": "1", "frequency": "stat", "duration_days": 1, "quantity": 1,
    }]}
    assert doctor.post(rx_url(draft["id"]), payload, format="json").status_code == 409


# --- Cancellation ---


def test_cancel_requires_reason_and_author(doctor, second_doctor, draft, amoxicillin):
    created = doctor.post(rx_url(draft["id"]), rx_payload(amoxicillin), format="json").json()
    cancel_url = f"/api/v1/prescriptions/{created['id']}/cancel/"

    assert doctor.post(cancel_url, {"reason": ""}, format="json").status_code == 400
    assert second_doctor.post(cancel_url, {"reason": "x"}, format="json").status_code == 403

    response = doctor.post(cancel_url, {"reason": "Changed treatment plan"}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert AuditLog.objects.filter(changes__cancel_reason="Changed treatment plan").exists()
