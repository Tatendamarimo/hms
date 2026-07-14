from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import roles
from apps.core.api import ClinicScopedViewSetMixin, get_active_clinic
from apps.core.permissions import RolePermission

from . import services
from .models import Invoice, ServiceItem, ServicePrice
from .serializers import (
    InvoiceSerializer,
    PaymentSerializer,
    ServiceItemSerializer,
    ServicePriceSerializer,
)

TILL_ROLES = [roles.CASHIER, roles.RECEPTIONIST]


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


class InvoiceDetailView(APIView):
    permission_classes = [RolePermission]
    role_map = {"get": [*TILL_ROLES, roles.ADMIN]}

    def get(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.filter(clinic=get_active_clinic(request))
            .prefetch_related("items", "payments"),
            pk=pk,
        )
        return Response(InvoiceSerializer(invoice).data)


class PaymentCreateView(APIView):
    permission_classes = [RolePermission]
    role_map = {"post": TILL_ROLES}

    def post(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.filter(clinic=get_active_clinic(request)), pk=pk
        )
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = services.record_payment(
                invoice,
                amount=serializer.validated_data["amount"],
                method=serializer.validated_data["method"],
                reference=serializer.validated_data.get("reference", ""),
                received_by=request.user,
            )
        except services.BillingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
