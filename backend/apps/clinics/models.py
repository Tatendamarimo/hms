from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, TimeStampedModel

# Defaults live in code so a clinic row only stores overrides (design §2.2).
# payment_before_consultation=True is the pilot default (design §8, Q2).
CLINIC_SETTING_DEFAULTS = {
    "payment_before_consultation": True,
    "allow_skip_triage": False,
    "vitals_reference_ranges": {
        "systolic": {"low": 90, "high": 140},
        "diastolic": {"low": 60, "high": 90},
        "pulse": {"low": 50, "high": 100},
        "temperature": {"low": 35.0, "high": 38.0},
        "spo2": {"low": 92, "high": 100},
    },
    # White-label branding (slice 10): per-tenant look, one codebase.
    # logo/favicon are URLs the clinic hosts (or data: URIs) — file upload
    # infrastructure (S3/MinIO) is a separate pre-go-live item.
    "branding": {
        "logo_url": "",
        "favicon_url": "",
        "primary_color": "#1e293b",
        "secondary_color": "#047857",
        "tagline": "",
    },
}


class Clinic(AuditedModel, TimeStampedModel):
    """A tenant. Every business record in the system belongs to exactly one
    clinic (FRD §7.1). v1 deploys with a single clinic; the schema does not
    know that."""

    name = models.CharField(max_length=200)
    code = models.SlugField(max_length=30, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_setting(self, key):
        if key not in CLINIC_SETTING_DEFAULTS:
            raise KeyError(f"Unknown clinic setting '{key}'")
        return self.settings.get(key, CLINIC_SETTING_DEFAULTS[key])

    @property
    def branding(self) -> dict:
        """Branding with defaults filled in — a clinic row stores only its
        overrides, and unknown keys are dropped so the payload shape is
        stable for every consumer (frontend theme, print headers)."""
        defaults = CLINIC_SETTING_DEFAULTS["branding"]
        overrides = self.settings.get("branding", {})
        return {key: overrides.get(key, default) for key, default in defaults.items()}


class ClinicMembership(AuditedModel, TimeStampedModel):
    """Grants a user access to a clinic. Roles are global Django groups;
    membership controls *where* those roles apply (FRD §3)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clinic_memberships",
    )
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="memberships")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "clinic"], name="unique_user_clinic"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.clinic}"
