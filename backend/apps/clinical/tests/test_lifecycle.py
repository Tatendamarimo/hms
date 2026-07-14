import pytest

from apps.clinical.models import Consultation, SignedConsultationImmutable
from apps.encounters.models import Encounter

from .conftest import CONSULTATIONS

pytestmark = pytest.mark.django_db


# --- Draft creation guards (edge cases first) ---


def test_only_the_claiming_doctor_can_open_the_consultation(claimed_visit, second_doctor):
    response = second_doctor.post(f"/api/v1/encounters/{claimed_visit.pk}/consultation/")
    assert response.status_code == 403


def test_consultation_requires_in_consultation_state(
    pay_after_clinic, receptionist, patient, doctor
):
    created = receptionist.post("/api/v1/encounters/", {"patient": patient.pk}, format="json")
    response = doctor.post(f"/api/v1/encounters/{created.json()['id']}/consultation/")
    assert response.status_code == 409


def test_only_one_root_consultation_per_visit(doctor, draft, claimed_visit):
    response = doctor.post(f"/api/v1/encounters/{claimed_visit.pk}/consultation/")
    assert response.status_code == 409


def test_draft_editable_by_author_only(second_doctor, draft):
    response = second_doctor.patch(
        f"{CONSULTATIONS}{draft['id']}/", {"clinical_notes": "hijack"}, format="json"
    )
    assert response.status_code == 403


# --- Signing ---


def test_cannot_sign_an_empty_consultation(doctor, draft):
    response = doctor.post(f"{CONSULTATIONS}{draft['id']}/sign/")
    assert response.status_code == 400
    assert "empty" in str(response.json())


def test_sign_freezes_record_and_moves_encounter_to_awaiting_payment(
    doctor, signable_draft, claimed_visit
):
    response = doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "signed"
    assert body["signed_at"] is not None

    claimed_visit.refresh_from_db()
    assert claimed_visit.status == Encounter.Status.AWAITING_PAYMENT

    # API refuses edits
    edit = doctor.patch(
        f"{CONSULTATIONS}{signable_draft['id']}/", {"clinical_notes": "changed"}, format="json"
    )
    assert edit.status_code == 409


def test_second_sign_attempt_conflicts(doctor, signable_draft):
    assert doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/").status_code == 200
    assert doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/").status_code == 409


def test_only_author_can_sign(second_doctor, signable_draft):
    assert second_doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/").status_code == 403


def test_signing_never_touches_the_invoice(doctor, signable_draft, claimed_visit):
    """ADR-0002 regression: sign mutates no billing state."""
    from apps.billing.models import Invoice, InvoiceItem

    items_before = InvoiceItem.all_objects.count()
    invoices_before = Invoice.all_objects.count()
    doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/")
    assert InvoiceItem.all_objects.count() == items_before
    assert Invoice.all_objects.count() == invoices_before


def test_signed_consultation_is_immutable_at_the_model_layer(doctor, signable_draft):
    doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/")
    consultation = Consultation.objects.get(pk=signable_draft["id"])
    consultation.clinical_notes = "tampered"
    with pytest.raises(SignedConsultationImmutable):
        consultation.save()
    with pytest.raises(SignedConsultationImmutable):
        consultation.save(update_fields=["clinical_notes"])


def test_voiding_a_signed_consultation_is_still_possible(doctor, signable_draft, doctor_user):
    doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/")
    consultation = Consultation.objects.get(pk=signable_draft["id"])
    consultation.void(by=doctor_user, reason="Recorded against the wrong patient")
    assert Consultation.all_objects.get(pk=consultation.pk).is_voided


# --- Amendments ---


@pytest.fixture
def signed(doctor, signable_draft):
    doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/")
    return signable_draft


def test_amendment_requires_reason(doctor, signed):
    response = doctor.post(f"{CONSULTATIONS}{signed['id']}/amend/", {}, format="json")
    assert response.status_code == 400


def test_cannot_amend_a_draft(doctor, signable_draft):
    # signable_draft is still a draft here
    response = doctor.post(
        f"{CONSULTATIONS}{signable_draft['id']}/amend/", {"reason": "x"}, format="json"
    )
    assert response.status_code == 409


def test_amendment_copies_content_and_chains_versions(doctor, signed):
    doctor.post(
        f"{CONSULTATIONS}{signed['id']}/diagnoses/", {"free_text": "URTI"}, format="json"
    )  # signed → should 409, diagnoses frozen too
    response = doctor.post(
        f"{CONSULTATIONS}{signed['id']}/amend/",
        {"reason": "Dosage clarification"},
        format="json",
    )
    assert response.status_code == 201
    amendment = response.json()
    assert amendment["version"] == 2
    assert amendment["status"] == "draft"
    assert amendment["amended_from"] == signed["id"]
    assert amendment["amendment_reason"] == "Dosage clarification"
    assert amendment["clinical_notes"] == "URTI, no red flags."

    original = doctor.get(f"{CONSULTATIONS}{signed['id']}/").json()
    assert original["amended_by_id"] == amendment["id"]


def test_a_version_can_be_amended_only_once(doctor, signed):
    first = doctor.post(
        f"{CONSULTATIONS}{signed['id']}/amend/", {"reason": "fix"}, format="json"
    )
    assert first.status_code == 201
    second = doctor.post(
        f"{CONSULTATIONS}{signed['id']}/amend/", {"reason": "fix again"}, format="json"
    )
    assert second.status_code == 409


def test_signing_an_amendment_does_not_move_the_encounter(doctor, signed, claimed_visit):
    amendment = doctor.post(
        f"{CONSULTATIONS}{signed['id']}/amend/", {"reason": "fix"}, format="json"
    ).json()
    claimed_visit.refresh_from_db()
    status_before = claimed_visit.status  # awaiting_payment

    assert doctor.post(f"{CONSULTATIONS}{amendment['id']}/sign/").status_code == 200
    claimed_visit.refresh_from_db()
    assert claimed_visit.status == status_before


def test_chain_endpoint_returns_all_versions(doctor, signed, claimed_visit):
    doctor.post(f"{CONSULTATIONS}{signed['id']}/amend/", {"reason": "fix"}, format="json")
    chain = doctor.get(f"/api/v1/encounters/{claimed_visit.pk}/consultation/").json()
    assert [c["version"] for c in chain] == [1, 2]
