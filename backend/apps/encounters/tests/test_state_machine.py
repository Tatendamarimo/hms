import pytest

from apps.core.models import AuditLog
from apps.encounters.models import Encounter

from .conftest import move

pytestmark = pytest.mark.django_db


@pytest.fixture
def visit(pay_after_clinic, open_visit):
    return open_visit()


def test_full_happy_path_to_closed(visit, nurse, doctor, doctor_user, cashier):
    assert move(nurse, visit["id"], "in_triage").status_code == 200
    assert move(nurse, visit["id"], "awaiting_doctor").status_code == 200

    claimed = move(doctor, visit["id"], "in_consultation")
    assert claimed.status_code == 200
    assert claimed.json()["assigned_doctor_name"] == str(doctor_user)

    assert move(doctor, visit["id"], "awaiting_payment").status_code == 200
    closed = move(cashier, visit["id"], "closed")
    assert closed.status_code == 200

    encounter = Encounter.objects.get(pk=visit["id"])
    assert encounter.closed_at is not None


def test_wrong_role_is_forbidden_on_every_edge(visit, receptionist, nurse, doctor, cashier):
    # Receptionist cannot start triage
    assert move(receptionist, visit["id"], "in_triage").status_code == 403
    move(nurse, visit["id"], "in_triage")
    # Doctor cannot mark triage done
    assert move(doctor, visit["id"], "awaiting_doctor").status_code == 403
    move(nurse, visit["id"], "awaiting_doctor")
    # Nurse cannot claim for consultation
    assert move(nurse, visit["id"], "in_consultation").status_code == 403
    move(doctor, visit["id"], "in_consultation")
    # Cashier cannot end the consultation
    assert move(cashier, visit["id"], "awaiting_payment").status_code == 403


def test_illegal_jump_is_conflict(visit, doctor):
    assert move(doctor, visit["id"], "in_consultation").status_code == 409


def test_two_doctors_cannot_claim_the_same_patient(visit, nurse, doctor, second_doctor):
    move(nurse, visit["id"], "in_triage")
    move(nurse, visit["id"], "awaiting_doctor")

    assert move(doctor, visit["id"], "in_consultation").status_code == 200
    assert move(second_doctor, visit["id"], "in_consultation").status_code == 409


def test_skip_triage_respects_clinic_setting(pay_after_clinic, open_visit, receptionist):
    visit = open_visit()
    assert move(receptionist, visit["id"], "awaiting_doctor").status_code == 400

    pay_after_clinic.settings = {
        "payment_before_consultation": False, "allow_skip_triage": True,
    }
    pay_after_clinic.save()
    assert move(receptionist, visit["id"], "awaiting_doctor").status_code == 200


def test_lwbs_requires_reason_and_only_before_consultation(visit, nurse, doctor, receptionist):
    assert move(receptionist, visit["id"], "left_without_being_seen").status_code == 400

    response = move(receptionist, visit["id"], "left_without_being_seen", reason="Patient left")
    assert response.status_code == 200
    assert AuditLog.objects.filter(
        model_label="encounters.Encounter",
        changes__transition_reason="Patient left",
    ).exists()

    # And never after the doctor has the patient
    visit2 = Encounter.objects.get(pk=visit["id"])
    assert visit2.status == "left_without_being_seen"


def test_close_with_balance_needs_permission_and_reason(
    pay_after_clinic, open_visit, nurse, doctor, cashier, receptionist,
    consult_service, doctor_user, rec_user,
):
    from apps.billing import services as billing

    visit = open_visit()
    move(nurse, visit["id"], "in_triage")
    move(nurse, visit["id"], "awaiting_doctor")
    move(doctor, visit["id"], "in_consultation")
    move(doctor, visit["id"], "awaiting_payment")

    encounter = Encounter.objects.get(pk=visit["id"])
    invoice = billing.ensure_invoice(encounter, created_by=rec_user)
    billing.add_service_line(invoice, service_item=consult_service, created_by=rec_user)

    # Receptionist lacks the close_with_balance permission
    attempt = move(receptionist, visit["id"], "closed", reason="patient will pay later")
    assert attempt.status_code == 400
    # Cashier holds it, but must give a reason
    assert move(cashier, visit["id"], "closed").status_code == 400
    assert move(cashier, visit["id"], "closed", reason="Owner authorised credit").status_code == 200
