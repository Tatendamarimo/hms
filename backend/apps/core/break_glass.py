"""Break-glass clinical access (FRD §3, §5.10; Slice 5 design).

Admin has NO standing clinical access. A grant is: one patient, read-only,
15 minutes, bound to the current session (dies with logout), and announced by
a high-visibility BREAK_GLASS audit entry carrying the mandatory reason.
No model — the session holds the grant, the audit log holds the record.

core keeps only session + audit mechanics; it takes patient identifiers as
plain values so it depends on no other app.
"""

from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import AuditLog

SESSION_KEY = "break_glass_grants"
GRANT_DURATION = timedelta(minutes=15)


def grant_access(request, *, clinic, patient_pk, patient_repr, reason: str):
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Break-glass access requires an explicit reason.")

    expires_at = timezone.now() + GRANT_DURATION
    grants = dict(request.session.get(SESSION_KEY, {}))
    grants[str(patient_pk)] = expires_at.isoformat()
    request.session[SESSION_KEY] = grants

    AuditLog.objects.create(
        user=request.user,
        clinic=clinic,
        action=AuditLog.Action.BREAK_GLASS,
        model_label="patients.Patient",
        object_pk=str(patient_pk),
        object_repr=patient_repr[:255],
        changes={"reason": reason, "expires_at": expires_at.isoformat()},
    )
    return expires_at


def has_active_grant(request, patient_pk) -> bool:
    grants = dict(request.session.get(SESSION_KEY, {}))
    raw = grants.get(str(patient_pk))
    if raw is None:
        return False
    expires_at = parse_datetime(raw)
    if expires_at is None or expires_at <= timezone.now():
        grants.pop(str(patient_pk), None)
        request.session[SESSION_KEY] = grants
        return False
    return True
