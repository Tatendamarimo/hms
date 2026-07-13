import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
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
def seeded_roles(db):
    call_command("seed_roles")


@pytest.fixture
def user_factory(db, seeded_roles):
    """make_user("dr.alan", roles.DOCTOR, clinic=clinic) -> user with roles + membership."""

    def make_user(username, *role_names, clinic=None):
        account = get_user_model().objects.create_user(username=username, password=PASSWORD)
        for name in role_names:
            account.groups.add(Group.objects.get(name=name))
        if clinic is not None:
            ClinicMembership.objects.create(user=account, clinic=clinic)
        return account

    return make_user


@pytest.fixture
def login():
    """Fresh client logged in as the given user through the real endpoint."""

    def _login(account):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/login/",
            {"username": account.username, "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 200, response.content
        return client

    return _login


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
