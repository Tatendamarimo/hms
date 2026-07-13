from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import AuditedModel


class User(AuditedModel, AbstractUser):
    """System user. Roles are Django groups (a user may hold several — FRD §3);
    clinic access is granted via clinics.ClinicMembership."""

    phone = models.CharField(max_length=30, blank=True)

    AUDIT_EXCLUDED_FIELDS = ("password", "last_login", "updated_at")

    class Meta:
        ordering = ["username"]

    @property
    def role_names(self) -> list[str]:
        return list(self.groups.values_list("name", flat=True))

    def __str__(self):
        return self.get_full_name() or self.username
