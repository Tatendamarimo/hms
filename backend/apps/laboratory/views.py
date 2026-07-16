from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import roles
from apps.clinical.models import Consultation
from apps.clinical.services import ConsultationPermissionError, ConsultationStateError
from apps.core.api import ClinicScopedViewSetMixin, get_active_clinic
from apps.core.permissions import RolePermission

from . import services
from .models import LabOrder
from .serializers import LabOrderCreateSerializer, LabOrderSerializer


def _translate(exc):
    if isinstance(exc, ConsultationPermissionError):
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)


class ConsultationLabOrdersView(APIView):
    """POST /consultations/{pk}/lab-orders/ — lives in laboratory (it owns the
    order), keeping the dependency direction laboratory -> clinical."""

    permission_classes = [RolePermission]
    role_map = {"post": [roles.DOCTOR]}

    def post(self, request, pk):
        consultation = get_object_or_404(
            Consultation.objects.filter(clinic=get_active_clinic(request)), pk=pk
        )
        serializer = LabOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = services.create_lab_order(
                consultation,
                by=request.user,
                service_items=serializer.validated_data["service_items"],
                instructions=serializer.validated_data["instructions"],
            )
        except (ConsultationStateError, ConsultationPermissionError) as exc:
            return _translate(exc)
        return Response(LabOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class LabOrderViewSet(
    ClinicScopedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = LabOrder.objects.prefetch_related("items__service_item")
    serializer_class = LabOrderSerializer
    permission_classes = [RolePermission]
    role_map = {
        "list": [roles.DOCTOR, roles.LAB_TECHNICIAN],
        "retrieve": [roles.DOCTOR, roles.LAB_TECHNICIAN],
        "cancel": [roles.DOCTOR],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        consultation = self.request.query_params.get("consultation")
        if consultation:
            queryset = queryset.filter(consultation_id=consultation)
        return queryset

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        try:
            order = services.cancel_lab_order(
                self.get_object(), by=request.user, reason=request.data.get("reason", "")
            )
        except (ConsultationStateError, ConsultationPermissionError) as exc:
            return _translate(exc)
        return Response(LabOrderSerializer(order).data)
