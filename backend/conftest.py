import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.clinics.models import Clinic, ClinicMembership

PASSWORD = "S3cure-Pass-1234"


@pytest.fixture
def clinic(db):
    return Clinic.objects.create(name="Harare Clinic", code="harare")


@pytest.fixture
def other_clinic(db):
    return Clinic.objects.create(name="Bulawayo Clinic", code="bulawayo")


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="nurse.emily",
        password=PASSWORD,
        first_name="Emily",
        last_name="Moyo",
    )


@pytest.fixture
def membership(user, clinic):
    return ClinicMembership.objects.create(user=user, clinic=clinic)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, user, membership):
    """Client logged in through the real login endpoint (session + active clinic)."""
    response = api_client.post(
        "/api/v1/auth/login/",
        {"username": user.username, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200, response.content
    return api_client
