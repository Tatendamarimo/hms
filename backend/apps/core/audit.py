"""Automatic mutation auditing.

Any concrete model inheriting AuditedModel gets create/update/void entries in
AuditLog with a before/after field diff, attributed via the request context
(middleware) or an explicit actor_context (tasks, commands). Auth events
(login, logout, failed login) are audited via Django's auth signals.

Reads of clinical records are audited explicitly by views via `log_read` /
`AuditedReadMixin` — Phase 1 clinical viewsets must use it (FRD §5.10).
"""

import datetime
import decimal

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save, pre_save

from .context import get_actor

_pending_diffs: dict = {}


def _serialize(value):
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _snapshot(instance) -> dict:
    excluded = getattr(instance, "AUDIT_EXCLUDED_FIELDS", ())
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name in excluded:
            continue
        data[field.name] = _serialize(field.value_from_object(instance))
    return data


def _actor_fields():
    from .models import AuditLog  # local import to avoid app-loading cycles

    actor = get_actor()
    user = None
    ip = None
    if actor:
        ip = actor.ip_address
        if actor.user_id:
            user = get_user_model().objects.filter(pk=actor.user_id).first()
    return AuditLog, user, ip


def _clinic_of(instance):
    clinic_id = getattr(instance, "clinic_id", None)
    if clinic_id:
        return clinic_id
    # The Clinic model itself is audited; it is its own clinic context.
    if instance._meta.label == "clinics.Clinic" and instance.pk:
        return instance.pk
    return None


def _write(action, instance, changes):
    audit_log, user, ip = _actor_fields()
    audit_log.objects.create(
        user=user,
        clinic_id=_clinic_of(instance),
        action=action,
        model_label=instance._meta.label,
        object_pk=str(instance.pk or ""),
        object_repr=str(instance)[:255],
        changes=changes,
        ip_address=ip,
    )


def _on_pre_save(sender, instance, **kwargs):
    if instance.pk:
        old = sender._base_manager.filter(pk=instance.pk).first()
        _pending_diffs[(sender._meta.label, instance.pk)] = _snapshot(old) if old else None


def _on_post_save(sender, instance, created, **kwargs):
    from .models import AuditLog

    new = _snapshot(instance)
    if created:
        _write(AuditLog.Action.CREATE, instance, {"after": new})
        return

    before = _pending_diffs.pop((sender._meta.label, instance.pk), None) or {}
    diff = {
        name: {"before": before.get(name), "after": value}
        for name, value in new.items()
        if before.get(name) != value
    }
    if not diff:
        return
    was_voided = "voided_at" in diff and diff["voided_at"]["before"] is None
    action = AuditLog.Action.VOID if was_voided else AuditLog.Action.UPDATE
    _write(action, instance, diff)


def log_read(user, instance, *, ip_address=None):
    """Audit a read of a clinical record (FRD §5.10: reads are logged too)."""
    from .models import AuditLog

    actor = get_actor()
    AuditLog.objects.create(
        user=user if user is not None and user.is_authenticated else None,
        clinic_id=_clinic_of(instance),
        action=AuditLog.Action.READ,
        model_label=instance._meta.label,
        object_pk=str(instance.pk or ""),
        object_repr=str(instance)[:255],
        ip_address=ip_address or (actor.ip_address if actor else None),
    )


class AuditedReadMixin:
    """DRF mixin: logs every retrieve() of a clinical record. Phase 1 clinical
    viewsets (consultations, results, …) must include this mixin."""

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        log_read(request.user, self.get_object())
        return response


def register_audited_models():
    from .models import AuditedModel

    for model in django_apps.get_models():
        if issubclass(model, AuditedModel) and not model._meta.abstract:
            uid = f"audit:{model._meta.label}"
            pre_save.connect(_on_pre_save, sender=model, dispatch_uid=f"{uid}:pre")
            post_save.connect(_on_post_save, sender=model, dispatch_uid=f"{uid}:post")


# --- Auth events ---


def _on_login(sender, request, user, **kwargs):
    from .models import AuditLog

    _write_auth(AuditLog.Action.LOGIN, user, request)


def _on_logout(sender, request, user, **kwargs):
    from .models import AuditLog

    if user is not None:
        _write_auth(AuditLog.Action.LOGOUT, user, request)


def _on_login_failed(sender, credentials, request=None, **kwargs):
    from .models import AuditLog

    username = credentials.get("username", "")
    AuditLog.objects.create(
        action=AuditLog.Action.LOGIN_FAILED,
        model_label="accounts.User",
        object_repr=str(username)[:255],
        changes={"username": str(username)},
        ip_address=_request_ip(request),
    )


def _request_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _write_auth(action, user, request):
    from .models import AuditLog

    AuditLog.objects.create(
        user=user,
        action=action,
        model_label="accounts.User",
        object_pk=str(user.pk),
        object_repr=str(user)[:255],
        ip_address=_request_ip(request),
    )


def connect_auth_signals():
    user_logged_in.connect(_on_login, dispatch_uid="audit:login")
    user_logged_out.connect(_on_logout, dispatch_uid="audit:logout")
    user_login_failed.connect(_on_login_failed, dispatch_uid="audit:login_failed")
