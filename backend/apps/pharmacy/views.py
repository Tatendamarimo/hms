from rest_framework import mixins, viewsets

from apps.accounts import roles
from apps.core.api import ClinicScopedViewSetMixin
from apps.core.permissions import RolePermission

from .models import Medication
from .serializers import MedicationSerializer


class MedicationViewSet(
    ClinicScopedViewSetMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """Doctor picklist (design §4). Catalog management is Admin work via the
    Django admin until the Phase 2 pharmacy module lands."""

    queryset = Medication.objects.filter(is_active=True)
    serializer_class = MedicationSerializer
    permission_classes = [RolePermission]
    pagination_class = None
    role_map = {"list": [roles.DOCTOR]}

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset[:30]
