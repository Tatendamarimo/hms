import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from apps.accounts.roles import ALL_ROLES

pytestmark = pytest.mark.django_db


def test_seed_roles_creates_all_frd_roles():
    call_command("seed_roles")
    assert set(Group.objects.values_list("name", flat=True)) == set(ALL_ROLES)
    assert len(ALL_ROLES) == 7


def test_seed_roles_is_idempotent():
    call_command("seed_roles")
    call_command("seed_roles")
    assert Group.objects.count() == 7
