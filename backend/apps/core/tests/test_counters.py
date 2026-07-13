import pytest

from apps.core.models import ClinicCounter

pytestmark = pytest.mark.django_db


def test_counter_increments_sequentially(clinic):
    values = [ClinicCounter.next_value(clinic, "mrn") for _ in range(3)]
    assert values == [1, 2, 3]


def test_counters_are_isolated_per_clinic_and_key(clinic, other_clinic):
    assert ClinicCounter.next_value(clinic, "mrn") == 1
    assert ClinicCounter.next_value(clinic, "invoice") == 1
    assert ClinicCounter.next_value(other_clinic, "mrn") == 1
    assert ClinicCounter.next_value(clinic, "mrn") == 2
