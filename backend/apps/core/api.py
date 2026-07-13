"""Clinic scoping for DRF views — the mechanism that makes forgetting tenancy
impossible: every Phase 1+ viewset over clinic data inherits this mixin."""

from rest_framework.exceptions import PermissionDenied

ACTIVE_CLINIC_SESSION_KEY = "active_clinic_id"


def get_active_clinic(request):
    """The clinic the user is currently working in, validated against their
    active memberships on every call (revoking a membership takes effect
    immediately, not at next login)."""
    from apps.clinics.models import Clinic

    clinic_id = request.session.get(ACTIVE_CLINIC_SESSION_KEY)
    if clinic_id is None:
        raise PermissionDenied("No active clinic selected.")
    clinic = (
        Clinic.objects.filter(
            pk=clinic_id,
            is_active=True,
            memberships__user=request.user,
            memberships__is_active=True,
        )
        .distinct()
        .first()
    )
    if clinic is None:
        raise PermissionDenied("You are not an active member of the selected clinic.")
    return clinic


class ClinicScopedViewSetMixin:
    """Filters every queryset to the active clinic and stamps clinic +
    created_by on create. Assumes the model inherits ClinicScopedModel."""

    def get_queryset(self):
        return super().get_queryset().filter(clinic=get_active_clinic(self.request))

    def perform_create(self, serializer):
        serializer.save(clinic=get_active_clinic(self.request), created_by=self.request.user)
