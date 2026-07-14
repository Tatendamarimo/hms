"""Consultation domain services — ALL lifecycle logic lives here.

Error contract (views translate): ConsultationPermissionError -> 403,
ConsultationStateError -> 409, rest_framework ValidationError -> 400.

ADR-0002: signing NEVER mutates the invoice — the consultation fee originates
at check-in. The only cross-app side effect of signing is the encounter
transition, taken through encounters.services.transition().
"""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import AuditLog
from apps.encounters.models import Encounter
from apps.encounters.services import transition

from .models import Consultation, ConsultationDiagnosis


class ConsultationStateError(Exception):
    """The record moved on (already signed/amended, wrong encounter state)."""


class ConsultationPermissionError(Exception):
    """Author-only rule violated."""


def _require_author(consultation, user):
    if consultation.doctor_id != user.pk:
        raise ConsultationPermissionError(
            "Only the authoring doctor may modify this consultation."
        )


def _require_draft(consultation):
    if consultation.status != Consultation.Status.DRAFT:
        raise ConsultationStateError("This consultation is signed and immutable.")


def create_draft(encounter, *, doctor) -> Consultation:
    if encounter.status != Encounter.Status.IN_CONSULTATION:
        raise ConsultationStateError(
            "A consultation can only be opened while the visit is in consultation."
        )
    if encounter.assigned_doctor_id != doctor.pk:
        raise ConsultationPermissionError(
            "Only the doctor who claimed this patient may open the consultation."
        )
    try:
        with transaction.atomic():
            return Consultation.objects.create(
                clinic=encounter.clinic,
                encounter=encounter,
                doctor=doctor,
                created_by=doctor,
            )
    except IntegrityError as exc:
        raise ConsultationStateError(
            "A consultation already exists for this visit."
        ) from exc


def edit_draft(consultation, *, by, **fields) -> Consultation:
    _require_author(consultation, by)
    _require_draft(consultation)
    editable = {"presenting_complaint", "clinical_notes", "treatment_plan"}
    unknown = set(fields) - editable
    if unknown:
        raise ValidationError({name: "Field is not editable." for name in unknown})
    for name, value in fields.items():
        setattr(consultation, name, value)
    consultation.save(update_fields=[*fields, "updated_at"])
    return consultation


def sign(consultation, *, by) -> Consultation:
    """Row-locked: a concurrent second sign re-reads status inside the lock
    and gets ConsultationStateError, never a double signature."""
    with transaction.atomic():
        locked = Consultation.objects.select_for_update().get(pk=consultation.pk)
        _require_author(locked, by)
        if locked.status != Consultation.Status.DRAFT:
            raise ConsultationStateError("This consultation is already signed.")
        if not locked.clinical_notes.strip() and not locked.diagnoses.exists():
            raise ValidationError(
                {"detail": "Cannot sign an empty consultation — record clinical "
                           "notes or at least one diagnosis."}
            )
        locked.status = Consultation.Status.SIGNED
        locked.signed_at = timezone.now()
        locked.save(update_fields=["status", "signed_at", "updated_at"])

        # Root sign ends the visit's clinical stage; an amendment signed later
        # must not touch an encounter that has already moved on (design §2.4).
        encounter = locked.encounter
        if encounter.status == Encounter.Status.IN_CONSULTATION:
            transition(encounter, to=Encounter.Status.AWAITING_PAYMENT, user=by)
    return locked


def amend(consultation, *, by, reason: str) -> Consultation:
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "An amendment reason is required."})
    with transaction.atomic():
        locked = Consultation.objects.select_for_update().get(pk=consultation.pk)
        _require_author(locked, by)
        if locked.status != Consultation.Status.SIGNED:
            raise ConsultationStateError("Only a signed consultation can be amended.")
        if locked.is_amended:
            raise ConsultationStateError(
                "This version has already been amended — amend the latest version."
            )
        amendment = Consultation.objects.create(
            clinic=locked.clinic,
            encounter=locked.encounter,
            doctor=by,
            created_by=by,
            presenting_complaint=locked.presenting_complaint,
            clinical_notes=locked.clinical_notes,
            treatment_plan=locked.treatment_plan,
            version=locked.version + 1,
            amended_from=locked,
            amendment_reason=reason,
        )
        for item in locked.diagnoses.all():
            ConsultationDiagnosis.objects.create(
                clinic=item.clinic,
                consultation=amendment,
                diagnosis=item.diagnosis,
                free_text=item.free_text,
                created_by=by,
            )
    return amendment


def add_diagnosis(consultation, *, by, diagnosis=None, free_text="") -> ConsultationDiagnosis:
    _require_author(consultation, by)
    _require_draft(consultation)
    free_text = (free_text or "").strip()
    if diagnosis is None and not free_text:
        raise ValidationError(
            {"detail": "Provide a coded diagnosis or free text (or both)."}
        )
    return ConsultationDiagnosis.objects.create(
        clinic=consultation.clinic,
        consultation=consultation,
        diagnosis=diagnosis,
        free_text=free_text,
        created_by=by,
    )


def remove_diagnosis(consultation, *, by, item_pk) -> None:
    """Draft-only working-document removal. Hard delete is correct here (the
    row never appeared in a signed record) but it still leaves an audit trail."""
    _require_author(consultation, by)
    _require_draft(consultation)
    try:
        item = consultation.diagnoses.get(pk=item_pk)
    except ConsultationDiagnosis.DoesNotExist:
        raise ValidationError({"detail": "No such diagnosis on this consultation."}) from None
    removed_repr = str(item)
    item.delete()
    AuditLog.objects.create(
        user=by,
        clinic=consultation.clinic,
        action=AuditLog.Action.UPDATE,
        model_label="clinical.Consultation",
        object_pk=str(consultation.pk),
        object_repr=str(consultation)[:255],
        changes={"removed_diagnosis": removed_repr},
    )
