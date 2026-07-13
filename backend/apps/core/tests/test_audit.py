import pytest
from django.contrib.auth import get_user_model

from apps.core.context import Actor, actor_context
from apps.core.models import AuditLog
from apps.testapp.models import Record

pytestmark = pytest.mark.django_db


def entries(action=None, model_label="testapp.Record"):
    qs = AuditLog.objects.filter(model_label=model_label)
    if action:
        qs = qs.filter(action=action)
    return qs


def test_create_is_audited_with_snapshot(clinic):
    record = Record.objects.create(clinic=clinic, name="Vitals", notes="initial")

    entry = entries(AuditLog.Action.CREATE).get()
    assert entry.object_pk == str(record.pk)
    assert entry.clinic_id == clinic.pk
    assert entry.changes["after"]["name"] == "Vitals"


def test_update_is_audited_with_field_diff(clinic):
    record = Record.objects.create(clinic=clinic, name="Vitals", notes="v1")
    record.name = "Vitals (corrected)"
    record.save()

    entry = entries(AuditLog.Action.UPDATE).get()
    assert entry.changes["name"] == {"before": "Vitals", "after": "Vitals (corrected)"}
    assert "notes" not in entry.changes  # unchanged fields are not recorded


def test_noop_save_writes_no_update_entry(clinic):
    record = Record.objects.create(clinic=clinic, name="Vitals")
    record.save()
    assert entries(AuditLog.Action.UPDATE).count() == 0


def test_void_is_audited_as_void_action(clinic, user):
    record = Record.objects.create(clinic=clinic, name="Vitals")
    record.void(by=user, reason="wrong patient")

    assert entries(AuditLog.Action.VOID).count() == 1
    assert entries(AuditLog.Action.UPDATE).count() == 0


def test_mutation_is_attributed_to_context_actor(clinic, user):
    with actor_context(Actor(user_id=user.pk, ip_address="10.0.0.9")):
        Record.objects.create(clinic=clinic, name="Attributed")

    entry = entries(AuditLog.Action.CREATE).get()
    assert entry.user == user
    assert entry.ip_address == "10.0.0.9"


def test_user_audit_never_contains_password(db):
    get_user_model().objects.create_user(username="dr.alan", password="Sup3r-Secret-99")

    entry = AuditLog.objects.filter(
        model_label="accounts.User", action=AuditLog.Action.CREATE
    ).get()
    assert "password" not in entry.changes["after"]
    assert "Sup3r-Secret-99" not in str(entry.changes)


def test_login_logout_and_failed_login_are_audited(api_client, user):
    from conftest import PASSWORD

    api_client.post(
        "/api/v1/auth/login/", {"username": user.username, "password": "wrong"}, format="json"
    )
    assert AuditLog.objects.filter(action=AuditLog.Action.LOGIN_FAILED).count() == 1

    api_client.post(
        "/api/v1/auth/login/", {"username": user.username, "password": PASSWORD}, format="json"
    )
    assert AuditLog.objects.filter(action=AuditLog.Action.LOGIN, user=user).count() == 1

    api_client.post("/api/v1/auth/logout/")
    assert AuditLog.objects.filter(action=AuditLog.Action.LOGOUT, user=user).count() == 1
