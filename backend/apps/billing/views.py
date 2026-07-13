from rest_framework import mixins, viewsets

from apps.accounts import roles
from apps.core.api import ClinicScopedViewSetMixin
from apps.core.permissions import RolePermission

from .models import ServiceItem, ServicePrice
from .serializers import ServiceItemSerializer, ServicePriceSerializer


class ServiceItemViewSet(
    ClinicScopedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Catalog is readable by every role (prices appear on invoices they all
    handle); managing it is Admin work (FRD §5.10). No destroy — services are
    deactivated, never deleted (invoice history references them)."""

    queryset = ServiceItem.objects.prefetch_related("prices")
    serializer_class = ServiceItemSerializer
    permission_classes = [RolePermission]
    role_map = {
        "list": roles.ALL_ROLES,
        "retrieve": roles.ALL_ROLES,
        "create": [roles.ADMIN],
        "update": [roles.ADMIN],
        "partial_update": [roles.ADMIN],
    }


class ServicePriceViewSet(
    ClinicScopedViewSetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Append-only: no update/destroy — price history is permanent (design §2.5)."""

    queryset = ServicePrice.objects.select_related("service")
    serializer_class = ServicePriceSerializer
    permission_classes = [RolePermission]
    role_map = {
        "list": roles.ALL_ROLES,
        "create": [roles.ADMIN],
    }
