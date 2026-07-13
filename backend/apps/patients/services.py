from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import ClinicCounter

from .models import Patient

MRN_COUNTER_KEY = "mrn"


def format_mrn(clinic, sequence: int) -> str:
    return f"{clinic.code.upper()}-{sequence:06d}"


def register_patient(*, clinic, registered_by, **data) -> Patient:
    """MRN issue + patient creation are one transaction: a failed insert never
    burns a number silently, and two concurrent registrations cannot collide."""
    with transaction.atomic():
        sequence = ClinicCounter.next_value(clinic, MRN_COUNTER_KEY)
        return Patient.objects.create(
            clinic=clinic,
            created_by=registered_by,
            mrn=format_mrn(clinic, sequence),
            consent_given_at=timezone.now(),
            consent_captured_by=registered_by,
            **data,
        )


def find_duplicate_candidates(clinic, *, national_id: str, phone: str):
    """Exact-match dedupe check on the two strong identifiers (design §2.1)."""
    query = Q()
    if national_id:
        query |= Q(national_id__iexact=national_id)
    if phone:
        query |= Q(phone=phone)
    if not query:
        return Patient.objects.none()
    return Patient.objects.filter(clinic=clinic).filter(query)
