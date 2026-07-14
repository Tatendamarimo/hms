"""Base model conventions — FRD §7.1.

Every business table gets timestamps + created_by. Clinical/financial tables
additionally get soft delete (void) semantics and a clinic FK. Mutations on
any model inheriting AuditedModel are written to AuditLog automatically.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class HardDeleteForbidden(Exception):
    """Raised when .delete() is called on clinical/financial data (FRD §7.1:
    soft delete only). Use .void(by=…, reason=…) instead."""


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        editable=False,
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(voided_at__isnull=True)

    def voided(self):
        return self.filter(voided_at__isnull=False)

    def delete(self):
        raise HardDeleteForbidden(
            "Bulk delete is forbidden on soft-delete models; void records individually."
        )


class SoftDeleteManager(models.Manager):
    """Default manager: voided records are invisible unless asked for."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).active()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    voided_at = models.DateTimeField(null=True, blank=True, editable=False)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        editable=False,
    )
    void_reason = models.TextField(blank=True, editable=False)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"

    @property
    def is_voided(self) -> bool:
        return self.voided_at is not None

    def void(self, *, by, reason: str):
        if self.is_voided:
            return
        if not reason or not reason.strip():
            raise ValueError("A void reason is required (FRD §7.1).")
        self.voided_at = timezone.now()
        self.voided_by = by
        self.void_reason = reason.strip()
        self.save(update_fields=["voided_at", "voided_by", "void_reason", "updated_at"])

    def delete(self, *args, hard: bool = False, **kwargs):
        if not hard:
            raise HardDeleteForbidden(
                f"{type(self).__name__} is clinical/financial data and cannot be hard-deleted; "
                "use .void(by=…, reason=…)."
            )
        return super().delete(*args, **kwargs)


class ClinicScopedQuerySet(models.QuerySet):
    def for_clinic(self, clinic):
        return self.filter(clinic=clinic)

    def for_user(self, user):
        """Restrict to clinics where the user holds an active membership."""
        return self.filter(
            clinic__memberships__user=user,
            clinic__memberships__is_active=True,
        )


class ClinicScopedModel(models.Model):
    """Every business table carries clinic_id from day one (FRD §7.1) so
    multi-clinic support is a deployment decision, not a schema migration."""

    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        abstract = True


class ClinicCounter(models.Model):
    """Per-clinic, gap-free-enough sequence source for MRNs, invoice and
    receipt numbers. Incremented under row lock inside the caller's
    transaction — two concurrent registrations can never share a number."""

    clinic = models.ForeignKey("clinics.Clinic", on_delete=models.CASCADE, related_name="+")
    key = models.CharField(max_length=30)
    value = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["clinic", "key"], name="unique_clinic_counter"),
        ]

    def __str__(self):
        return f"{self.clinic_id}:{self.key}={self.value}"

    @classmethod
    def next_value(cls, clinic, key: str) -> int:
        from django.db import transaction

        with transaction.atomic():
            cls.objects.get_or_create(clinic=clinic, key=key)
            counter = cls.objects.select_for_update().get(clinic=clinic, key=key)
            counter.value += 1
            counter.save(update_fields=["value"])
            return counter.value


class AuditedModel(models.Model):
    """Opt-in marker: any concrete subclass has create/update/void mutations
    written to AuditLog automatically (registered in CoreConfig.ready)."""

    AUDIT_EXCLUDED_FIELDS = ("password", "last_login", "updated_at")

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """Append-only record of who did what, when, to which record (FRD §5.10).

    No FK to the audited object (it may be in any table); model_label +
    object_pk identify it. Never exposed for write through any API.
    """

    class Action(models.TextChoices):
        CREATE = "create"
        UPDATE = "update"
        VOID = "void"
        READ = "read"
        LOGIN = "login"
        LOGOUT = "logout"
        LOGIN_FAILED = "login_failed"
        BREAK_GLASS = "break_glass"

    at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_entries",
        editable=False,
    )
    clinic = models.ForeignKey(
        "clinics.Clinic",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        editable=False,
    )
    action = models.CharField(max_length=16, choices=Action.choices, editable=False)
    model_label = models.CharField(max_length=100, editable=False)
    object_pk = models.CharField(max_length=64, blank=True, editable=False)
    object_repr = models.CharField(max_length=255, blank=True, editable=False)
    changes = models.JSONField(default=dict, blank=True, editable=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["model_label", "object_pk"]),
            models.Index(fields=["user", "at"]),
        ]
        ordering = ["-at"]

    def __str__(self):
        return f"{self.at:%Y-%m-%d %H:%M:%S} {self.action} {self.model_label}#{self.object_pk}"
