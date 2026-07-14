"""Encounter state machine (design §2.2) — the single source of truth for
which transitions exist, who may perform them, and which guards apply.
Views never mutate Encounter.status directly; they call services.transition().
"""

from dataclasses import dataclass, field
from typing import Callable

from apps.accounts import roles

from .models import Encounter

Status = Encounter.Status


class TransitionError(Exception):
    """Base class — views translate subclasses to HTTP statuses."""


class IllegalTransition(TransitionError):
    """No such edge from the current state (HTTP 409 — state moved on)."""


class TransitionForbidden(TransitionError):
    """Edge exists but the user's role may not take it (HTTP 403)."""


class GuardFailed(TransitionError):
    """Edge exists, role fits, but a business rule blocks it (HTTP 400)."""


def _guard_prepayment(encounter, user, reason):
    """Payment-first clinics: nothing leaves 'waiting' until the check-in
    invoice is settled (design §2.2 / decision Q2)."""
    if not encounter.clinic.get_setting("payment_before_consultation"):
        return
    from apps.billing.services import prepayment_satisfied  # boundary: services only

    if not prepayment_satisfied(encounter):
        raise GuardFailed(
            "This clinic collects the consultation fee at check-in; "
            "the invoice must be settled before the patient can proceed."
        )


def _guard_skip_triage(encounter, user, reason):
    if not encounter.clinic.get_setting("allow_skip_triage"):
        raise GuardFailed("This clinic does not allow skipping triage.")


def _guard_settled_or_authorized(encounter, user, reason):
    from apps.billing.models import Invoice  # read-only balance check

    invoice = Invoice.objects.filter(encounter=encounter).first()
    balance = invoice.balance if invoice else 0
    if balance <= 0:
        return
    if not user.has_perm("encounters.close_with_balance"):
        raise GuardFailed(
            f"Invoice has an outstanding balance of {balance}; closing requires "
            "the 'close with balance' permission."
        )
    if not reason.strip():
        raise GuardFailed("Closing with an outstanding balance requires a reason.")


def _guard_reason_required(encounter, user, reason):
    if not reason.strip():
        raise GuardFailed("A reason is required for this transition.")


@dataclass(frozen=True)
class Rule:
    roles: tuple[str, ...]
    guards: tuple[Callable, ...] = field(default_factory=tuple)


RULES: dict[tuple[str, str], Rule] = {
    (Status.WAITING, Status.IN_TRIAGE): Rule(
        roles=(roles.NURSE,), guards=(_guard_prepayment,)
    ),
    (Status.WAITING, Status.AWAITING_DOCTOR): Rule(
        roles=(roles.RECEPTIONIST,), guards=(_guard_skip_triage, _guard_prepayment)
    ),
    (Status.IN_TRIAGE, Status.AWAITING_DOCTOR): Rule(roles=(roles.NURSE,)),
    (Status.AWAITING_DOCTOR, Status.IN_CONSULTATION): Rule(roles=(roles.DOCTOR,)),
    (Status.IN_CONSULTATION, Status.AWAITING_PAYMENT): Rule(roles=(roles.DOCTOR,)),
    (Status.AWAITING_PAYMENT, Status.CLOSED): Rule(
        roles=(roles.CASHIER, roles.RECEPTIONIST),
        guards=(_guard_settled_or_authorized,),
    ),
}

# A patient can walk out any time before seeing the doctor (design §2.2)
for _pre in (Status.WAITING, Status.IN_TRIAGE, Status.AWAITING_DOCTOR):
    RULES[(_pre, Status.LWBS)] = Rule(
        roles=(roles.RECEPTIONIST, roles.NURSE), guards=(_guard_reason_required,)
    )


def get_rule(current: str, target: str) -> Rule:
    try:
        return RULES[(current, target)]
    except KeyError:
        raise IllegalTransition(
            f"Cannot move an encounter from '{current}' to '{target}'."
        ) from None
