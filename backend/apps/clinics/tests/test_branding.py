"""Slice 10 PR1: white-label branding — defaults, overrides, public endpoint."""

import pytest

from apps.clinics.models import CLINIC_SETTING_DEFAULTS, Clinic

pytestmark = pytest.mark.django_db

BRANDING_URL = "/api/v1/clinics/branding/"


# --- edges first ---


def test_public_branding_needs_no_session(api_client, clinic):
    response = api_client.get(BRANDING_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Harare Clinic"
    assert body["branding"] == CLINIC_SETTING_DEFAULTS["branding"]


def test_multi_clinic_host_leaks_nothing(api_client, clinic, other_clinic):
    clinic.settings = {"branding": {"logo_url": "https://harare.example/logo.png"}}
    clinic.save()
    body = api_client.get(BRANDING_URL).json()
    assert body["name"] == "HMS"
    assert body["branding"]["logo_url"] == ""


def test_no_clinic_still_answers(api_client, db):
    body = api_client.get(BRANDING_URL).json()
    assert body["name"] == "HMS"


def test_inactive_clinic_is_ignored(api_client, clinic, other_clinic):
    other_clinic.is_active = False
    other_clinic.save()
    assert api_client.get(BRANDING_URL).json()["name"] == "Harare Clinic"


# --- overrides and shape ---


def test_overrides_merge_over_defaults_and_unknown_keys_drop(clinic):
    clinic.settings = {
        "branding": {
            "primary_color": "#123456",
            "logo_url": "https://c.example/logo.svg",
            "rogue_key": "ignored",
        }
    }
    clinic.save()
    branding = Clinic.objects.get(pk=clinic.pk).branding
    assert branding["primary_color"] == "#123456"
    assert branding["logo_url"] == "https://c.example/logo.svg"
    assert branding["secondary_color"] == (
        CLINIC_SETTING_DEFAULTS["branding"]["secondary_color"]
    )
    assert "rogue_key" not in branding


def test_me_carries_the_active_clinic_branding(user_factory, login, clinic):
    from apps.accounts import roles

    clinic.settings = {"branding": {"primary_color": "#0f766e"}}
    clinic.save()
    client = login(user_factory("rec.brand", roles.RECEPTIONIST, clinic=clinic))
    me = client.get("/api/v1/auth/me/").json()
    assert me["active_clinic"]["branding"]["primary_color"] == "#0f766e"
    assert me["clinics"][0]["branding"]["primary_color"] == "#0f766e"


def test_print_header_uses_branding(user_factory, login, clinic):
    from apps.accounts import roles
    from apps.patients.services import register_patient

    clinic.settings = {
        "branding": {"logo_url": "https://c.example/logo.png", "primary_color": "#123456"}
    }
    clinic.save()
    rec_user = user_factory("rec.print", roles.RECEPTIONIST, clinic=clinic)
    patient = register_patient(
        clinic=clinic, registered_by=rec_user,
        first_name="Brand", last_name="Test",
        date_of_birth="1990-01-01", sex="M",
    )
    page = login(rec_user).get(f"/print/registration/{patient.pk}/")
    assert page.status_code == 200
    html = page.content.decode()
    assert "https://c.example/logo.png" in html
    assert "#123456" in html
