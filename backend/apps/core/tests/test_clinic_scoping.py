import pytest

from apps.testapp.models import Record

pytestmark = pytest.mark.django_db


def test_for_user_returns_only_active_membership_clinics(user, clinic, other_clinic, membership):
    mine = Record.objects.create(clinic=clinic, name="mine")
    Record.objects.create(clinic=other_clinic, name="not mine")

    from apps.core.models import ClinicScopedQuerySet

    qs = ClinicScopedQuerySet(Record).for_user(user)
    assert list(qs) == [mine]


def test_for_user_excludes_deactivated_memberships(user, clinic, membership):
    Record.objects.create(clinic=clinic, name="was mine")
    membership.is_active = False
    membership.save()

    from apps.core.models import ClinicScopedQuerySet

    assert ClinicScopedQuerySet(Record).for_user(user).count() == 0
