from decimal import Decimal

from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import roles
from apps.core.api import ClinicScopedViewSetMixin, get_active_clinic
from apps.core.permissions import RolePermission

from . import services
from .models import Invoice, InvoiceItem, Payment, ServiceItem, ServicePrice
from .serializers import (
    CashUpCloseSerializer,
    CashUpSerializer,
    InvoiceItemCreateSerializer,
    InvoiceItemSerializer,
    InvoiceSerializer,
    PaymentSerializer,
    ServiceItemSerializer,
    ServicePriceSerializer,
    UnpaidInvoiceSerializer,
)

TILL_ROLES = [roles.CASHIER, roles.RECEPTIONIST]

BILLING_ERROR_STATUS = {
    services.BillingError: status.HTTP_400_BAD_REQUEST,
    services.BillingPermissionError: status.HTTP_403_FORBIDDEN,
    services.BillingConflict: status.HTTP_409_CONFLICT,
}


def _billing_error(exc) -> Response:
    return Response({"detail": str(exc)}, status=BILLING_ERROR_STATUS[type(exc)])


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
            return _billing_error(exc)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class InvoiceItemCreateView(APIView):
    """Desk additions: catalog service lines for the till roles; discount
    lines additionally gated by billing.apply_discount (checked in the
    service, seeded Admin-only — hence Admin passes the role gate here)."""

    permission_classes = [RolePermission]
    role_map = {"post": [*TILL_ROLES, roles.ADMIN]}

    def post(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.filter(clinic=get_active_clinic(request)), pk=pk
        )
        serializer = InvoiceItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            if data["item_type"] == InvoiceItem.ItemType.DISCOUNT:
                item = services.apply_discount(
                    invoice, by=request.user, amount=data["amount"], reason=data["reason"]
                )
            else:
                item = services.add_manual_line(
                    invoice,
                    service_item=data["service_item"],
                    by=request.user,
                    quantity=data["quantity"],
                )
        except tuple(BILLING_ERROR_STATUS) as exc:
            return _billing_error(exc)
        return Response(InvoiceItemSerializer(item).data, status=status.HTTP_201_CREATED)


class InvoiceItemVoidView(APIView):
    permission_classes = [RolePermission]
    role_map = {"post": [roles.ADMIN]}

    def post(self, request, pk, item_pk):
        item = get_object_or_404(
            InvoiceItem.all_objects.filter(
                clinic=get_active_clinic(request), invoice_id=pk
            ),
            pk=item_pk,
        )
        try:
            item = services.void_line(item, by=request.user, reason=request.data.get("reason", ""))
        except tuple(BILLING_ERROR_STATUS) as exc:
            return _billing_error(exc)
        return Response(InvoiceItemSerializer(item).data)


class CashUpView(APIView):
    """GET = live preview of the requesting cashier's open drawer (computed,
    creates nothing); POST = count-and-close in one atomic step (design §4:
    `billing/cashup/` GET current, POST close — Cashier only)."""

    permission_classes = [RolePermission]
    role_map = {"get": [roles.CASHIER], "post": [roles.CASHIER]}

    def get(self, request):
        preview = services.drawer_preview(get_active_clinic(request), request.user)
        return Response(
            {
                "expected_total": str(preview["expected_total"]),
                "payment_count": preview["payment_count"],
                "period_start": preview["period_start"],
                "previous_cash_up_at": preview["previous_cash_up_at"],
                "payments": PaymentSerializer(preview["payments"], many=True).data,
            }
        )

    def post(self, request):
        serializer = CashUpCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cash_up = services.close_cash_up(
                get_active_clinic(request),
                cashier=request.user,
                **serializer.validated_data,
            )
        except tuple(BILLING_ERROR_STATUS) as exc:
            return _billing_error(exc)
        return Response(CashUpSerializer(cash_up).data, status=status.HTTP_201_CREATED)


class UnpaidBalancesView(APIView):
    """Per-patient outstanding balances from derived invoice status
    (FRD §5.7). Patients owing the most first."""

    permission_classes = [RolePermission]
    role_map = {"get": [roles.CASHIER, roles.ADMIN]}

    def get(self, request):
        invoices = services.unpaid_invoices(get_active_clinic(request))
        by_patient: dict[int, dict] = {}
        for invoice in invoices:
            patient = invoice.encounter.patient
            entry = by_patient.setdefault(
                patient.pk,
                {
                    "patient": {
                        "id": patient.pk,
                        "mrn": patient.mrn,
                        "full_name": patient.full_name,
                    },
                    "outstanding": Decimal("0.00"),
                    "invoices": [],
                },
            )
            entry["outstanding"] += invoice.outstanding
            entry["invoices"].append(UnpaidInvoiceSerializer(invoice).data)
        results = sorted(
            by_patient.values(), key=lambda entry: entry["outstanding"], reverse=True
        )
        for entry in results:
            entry["outstanding"] = str(entry["outstanding"])
        return Response({"count": len(results), "results": results})


class PaymentReverseView(APIView):
    permission_classes = [RolePermission]
    role_map = {"post": [roles.CASHIER, roles.ADMIN]}

    def post(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.filter(clinic=get_active_clinic(request)), pk=pk
        )
        try:
            reversal = services.reverse_payment(
                payment, by=request.user, reason=request.data.get("reason", "")
            )
        except tuple(BILLING_ERROR_STATUS) as exc:
            return _billing_error(exc)
        return Response(PaymentSerializer(reversal).data, status=status.HTTP_201_CREATED)
