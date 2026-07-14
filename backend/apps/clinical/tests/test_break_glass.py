import pytest
from django.utils import timezone

from apps.core.break_glass import SESSION_KEY
from apps.core.models import AuditLog

from .conftest import CONSULTATIONS

pytestmark = pytest.mark.django_db

BREAK_GLASS = "/api/v1/break-glass/"


@pytest.fixture
def signed_consultation(doctor, signable_draft):
    doctor.post(f"{CONSULTATIONS}{signable_draft['id']}/sign/")
    return signable_draft


def summary_url(patient):
    return f"/api/v1/patients/{patient.pk}/summary/"


# --- Authorization edges first ---


def test_admin_has_no_standing_clinical_access(admin, patient, signed_consultation):
    assert admin.get(summary_url(patient)).status_code == 403
    assert admin.get(f"/api/v1/patients/{patient.pk}/timeline/").status_code == 403
    assert admin.get(f"{CONSULTATIONS}{signed_consultation['id']}/").status_code == 403


def test_grant_requires_reason(admin, patient):
    response = admin.post(BREAK_GLASS, {"patient": patient.pk, "reason": "  "}, format="json")
    assert response.status_code == 400


def test_only_admin_can_break_glass(nurse, doctor, receptionist, patient):
    for client in (nurse, doctor, receptionist):
        response = client.post(
            BREAK_GLASS, {"patient": patient.pk, "reason": "curious"}, format="json"
        )
        assert response.status_code == 403


def test_grant_is_patient_scoped(admin, patient, clinic, rec_user):
    import datetime

    from apps.patients.services import register_patient

    other = register_patient(
        clinic=clinic, registered_by=rec_user, first_name="Rudo", last_name="Ncube",
        date_of_birth=datetime.date(1985, 2, 2), sex="F",
    )
    admin.post(BREAK_GLASS, {"patient": patient.pk, "reason": "Complaint review"}, format="json")

    assert admin.get(summary_url(patient)).status_code == 200
    assert admin.get(summary_url(other)).status_code == 403


def test_grant_expires(admin, patient):
    admin.post(BREAK_GLASS, {"patient": patient.pk, "reason": "Complaint review"}, format="json")
    assert admin.get(summary_url(patient)).status_code == 200

    session = admin.session
    session[SESSION_KEY] = {
        str(patient.pk): (timezone.now() - timezone.timedelta(minutes=1)).isoformat()
    }
    session.save()
    assert admin.get(summary_url(patient)).status_code == 403


def test_grant_is_read_only_admin_still_cannot_write(admin, patient, signed_consultation):
    admin.post(BREAK_GLASS, {"patient": patient.pk, "reason": "review"}, format="json")
    response = admin.post(
        f"{CONSULTATIONS}{signed_consultation['id']}/amend/", {"reason": "x"}, format="json"
    )
    assert response.status_code == 403


# --- Audit trail ---


def test_break_glass_writes_prominent_audit_entry(admin, patient):
    admin.post(
        BREAK_GLASS, {"patient": patient.pk, "reason": "Legal records request"}, format="json"
    )
    entry = AuditLog.objects.get(action=AuditLog.Action.BREAK_GLASS)
    assert entry.object_pk == str(patient.pk)
    assert entry.changes["reason"] == "Legal records request"
    assert entry.user.username == "admin.tino"


def test_reads_under_grant_are_flagged(admin, patient, signed_consultation, claimed_visit):
    admin.post(BREAK_GLASS, {"patient": patient.pk, "reason": "review"}, format="json")
    admin.get(summary_url(patient))
    admin.get(f"{CONSULTATIONS}{signed_consultation['id']}/")
    admin.get(f"/api/v1/encounters/{claimed_visit.pk}/vitals/")

    flagged = AuditLog.objects.filter(action=AuditLog.Action.READ, changes__break_glass=True)
    assert flagged.count() == 3


def test_doctor_reads_are_audited_without_flag(doctor, signed_consultation):
    doctor.get(f"{CONSULTATIONS}{signed_consultation['id']}/")
    entry = AuditLog.objects.get(
        action=AuditLog.Action.READ, model_label="clinical.Consultation"
    )
    assert entry.changes == {}
