from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import AuditLog

from .models import Encounter
from .state_machine import TransitionForbidden, get_rule


def open_encounter(*, clinic, patient, opened_by, type, notes="", checkin_service=None):
    """Check-in (design §2.2). In payment-first clinics the consultation fee
    line is created here so the desk can take payment immediately."""
    if patient.clinic_id != clinic.pk:
        raise ValidationError({"patient": "Patient belongs to a different clinic."})
    if patient.encounters.filter(status__in=Encounter.OPEN_STATUSES).exists():
        raise ValidationError({"patient": "This patient already has an open visit."})

    if checkin_service is not None and checkin_service.clinic_id != clinic.pk:
        raise ValidationError({"checkin_service": "Service belongs to a different clinic."})

    payment_first = clinic.get_setting("payment_before_consultation")
    if payment_first and checkin_service is None:
        raise ValidationError(
            {"checkin_service": "This clinic bills the consultation fee at check-in; "
                                "select the consultation service."}
        )

    with transaction.atomic():
        encounter = Encounter.objects.create(
            clinic=clinic,
            patient=patient,
            type=type,
            notes=notes,
            created_by=opened_by,
        )
        if checkin_service is not None:
            from apps.billing import services as billing  # boundary: services only

            invoice = billing.ensure_invoice(encounter, created_by=opened_by)
            try:
                billing.add_service_line(
                    invoice, service_item=checkin_service, created_by=opened_by
                )
            except billing.BillingError as exc:
                raise ValidationError({"checkin_service": str(exc)}) from exc
    return encounter


def transition(encounter, *, to, user, reason=""):
    """Applies one state-machine edge under a row lock. Concurrency-safe:
    the rule is resolved against the CURRENT status inside the lock, so a
    stale client (or a second doctor claiming the same patient) gets
    IllegalTransition, never a silent double-apply."""
    with transaction.atomic():
        locked = Encounter.objects.select_for_update().get(pk=encounter.pk)
        rule = get_rule(locked.status, to)

        if not set(rule.roles) & set(user.role_names):
            raise TransitionForbidden(
                f"Your role does not permit moving this visit to '{to}'."
            )
        for guard in rule.guards:
            guard(locked, user, reason)

        update_fields = ["status", "updated_at"]
        if to == Encounter.Status.IN_CONSULTATION:
            locked.assigned_doctor = user
            update_fields.append("assigned_doctor")
        if to in (Encounter.Status.CLOSED, Encounter.Status.LWBS):
            locked.closed_at = timezone.now()
            update_fields.append("closed_at")

        locked.status = to
        locked.save(update_fields=update_fields)

        if reason.strip():
            AuditLog.objects.create(
                user=user,
                clinic=locked.clinic,
                action=AuditLog.Action.UPDATE,
                model_label="encounters.Encounter",
                object_pk=str(locked.pk),
                object_repr=str(locked)[:255],
                changes={"transition_reason": reason.strip(), "to": to},
            )
    return locked
