import pytest

from apps.core.models import HardDeleteForbidden
from apps.testapp.models import Record

pytestmark = pytest.mark.django_db


@pytest.fixture
def record(clinic):
    return Record.objects.create(clinic=clinic, name="BP reading")


def test_void_hides_record_from_default_manager(record, user):
    record.void(by=user, reason="Entered against the wrong patient")

    assert Record.objects.count() == 0
    assert Record.all_objects.count() == 1

    voided = Record.all_objects.get(pk=record.pk)
    assert voided.is_voided
    assert voided.voided_by == user
    assert voided.void_reason == "Entered against the wrong patient"
    assert voided.voided_at is not None


def test_void_requires_a_reason(record, user):
    with pytest.raises(ValueError, match="reason"):
        record.void(by=user, reason="   ")


def test_void_is_idempotent(record, user):
    record.void(by=user, reason="duplicate")
    first_voided_at = record.voided_at
    record.void(by=user, reason="again")
    assert record.voided_at == first_voided_at
    assert record.void_reason == "duplicate"


def test_hard_delete_is_forbidden(record):
    with pytest.raises(HardDeleteForbidden):
        record.delete()
    assert Record.all_objects.filter(pk=record.pk).exists()


def test_bulk_delete_is_forbidden(record):
    with pytest.raises(HardDeleteForbidden):
        Record.all_objects.all().delete()


def test_explicit_hard_delete_escape_hatch(record):
    record.delete(hard=True)
    assert Record.all_objects.count() == 0
