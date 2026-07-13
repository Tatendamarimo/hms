import pytest

from conftest import PASSWORD

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login/"
ME = "/api/v1/auth/me/"


def test_csrf_endpoint_sets_cookie(api_client):
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    assert "csrftoken" in response.cookies


def test_login_returns_identity_and_auto_selects_single_clinic(api_client, user, membership):
    response = api_client.post(
        LOGIN, {"username": user.username, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "nurse.emily"
    assert data["active_clinic"]["code"] == "harare"
    assert [c["code"] for c in data["clinics"]] == ["harare"]


def test_login_rejects_bad_credentials_vaguely(api_client, user):
    response = api_client.post(
        LOGIN, {"username": user.username, "password": "nope"}, format="json"
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials."}


def test_me_requires_authentication(api_client):
    assert api_client.get(ME).status_code == 403


def test_logout_ends_session(auth_client):
    assert auth_client.get(ME).status_code == 200
    auth_client.post("/api/v1/auth/logout/")
    assert auth_client.get(ME).status_code == 403


def test_switch_clinic_rejects_non_member(auth_client, other_clinic):
    response = auth_client.post(
        "/api/v1/auth/clinic/", {"clinic_id": other_clinic.pk}, format="json"
    )
    assert response.status_code == 403


def test_switch_clinic_accepts_member(auth_client, user, other_clinic):
    from apps.clinics.models import ClinicMembership

    ClinicMembership.objects.create(user=user, clinic=other_clinic)
    response = auth_client.post(
        "/api/v1/auth/clinic/", {"clinic_id": other_clinic.pk}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["active_clinic"]["code"] == "bulawayo"


def test_my_clinics_lists_active_memberships(auth_client):
    response = auth_client.get("/api/v1/clinics/mine/")
    assert response.status_code == 200
    assert [c["code"] for c in response.json()] == ["harare"]
