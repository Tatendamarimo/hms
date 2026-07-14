from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import roles
from apps.core.api import ClinicScopedViewSetMixin, get_active_clinic
from apps.core.audit import log_read
from apps.core.break_glass import has_active_grant
from apps.core.permissions import RolePermission
from apps.encounters.models import Encounter

from . import services
from .models import Consultation, Diagnosis
from .serializers import (
    AddDiagnosisSerializer,
    AmendSerializer,
    ConsultationDiagnosisSerializer,
    ConsultationEditSerializer,
    ConsultationSerializer,
    DiagnosisSerializer,
)


def _translate(exc):
    if isinstance(exc, services.ConsultationPermissionError):
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)


def _clinical_read(request, patient_pk) -> tuple[bool, bool]:
    """(allowed, via_break_glass) for consultation reads: doctors by role;
    Admin read-only under an active grant (design: minimal scope)."""
    user_roles = set(request.user.role_names)
    if roles.DOCTOR in user_roles:
        return True, False
    if roles.ADMIN in user_roles and has_active_grant(request, patient_pk):
        return True, True
    return False, False


class DiagnosisViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Global picklist — deliberately not clinic-scoped."""

    serializer_class = DiagnosisSerializer
    permission_classes = [RolePermission]
    pagination_class = None
    role_map = {"list": [roles.DOCTOR]}

    def get_queryset(self):
        queryset = Diagnosis.objects.filter(is_active=True)
        query = self.request.query_params.get("q", "").strip()
        if query:
            from django.db.models import Q

            queryset = queryset.filter(Q(code__istartswith=query) | Q(name__icontains=query))
        return queryset[:30]


class EncounterConsultationView(APIView):
    """POST opens the draft (claim-holder only); GET returns the full version
    chain for the visit. Lives in clinical, keeping the dependency direction
    clinical -> encounters."""

    permission_classes = [RolePermission]
    role_map = {"post": [roles.DOCTOR], "get": [roles.DOCTOR, roles.ADMIN]}

    def post(self, request, pk):
        encounter = get_object_or_404(
            Encounter.objects.filter(clinic=get_active_clinic(request)), pk=pk
        )
        try:
            consultation = services.create_draft(encounter, doctor=request.user)
        except (services.ConsultationStateError, services.ConsultationPermissionError) as exc:
            return _translate(exc)
        return Response(
            ConsultationSerializer(consultation).data, status=status.HTTP_201_CREATED
        )

    def get(self, request, pk):
        encounter = get_object_or_404(
            Encounter.objects.filter(clinic=get_active_clinic(request)), pk=pk
        )
        allowed, via_break_glass = _clinical_read(request, encounter.patient_id)
        if not allowed:
            return Response(
                {"detail": "Break-glass access required."}, status=status.HTTP_403_FORBIDDEN
            )
        log_read(request.user, encounter, via_break_glass=via_break_glass)
        chain = Consultation.objects.filter(encounter=encounter).order_by("version")
        return Response(ConsultationSerializer(chain, many=True).data)


class ConsultationViewSet(
    ClinicScopedViewSetMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Consultation.objects.select_related(
        "doctor", "encounter"
    ).prefetch_related("diagnoses__diagnosis")
    serializer_class = ConsultationSerializer
    permission_classes = [RolePermission]
    role_map = {
        "retrieve": [roles.DOCTOR, roles.ADMIN],
        "partial_update": [roles.DOCTOR],
        "sign": [roles.DOCTOR],
        "amend": [roles.DOCTOR],
        "diagnoses": [roles.DOCTOR],
        "remove_diagnosis": [roles.DOCTOR],
    }

    def retrieve(self, request, *args, **kwargs):
        consultation = self.get_object()
        allowed, via_break_glass = _clinical_read(request, consultation.encounter.patient_id)
        if not allowed:
            return Response(
                {"detail": "Break-glass access required."}, status=status.HTTP_403_FORBIDDEN
            )
        log_read(request.user, consultation, via_break_glass=via_break_glass)
        return Response(ConsultationSerializer(consultation).data)

    def partial_update(self, request, *args, **kwargs):
        serializer = ConsultationEditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            consultation = services.edit_draft(
                self.get_object(), by=request.user, **serializer.validated_data
            )
        except (services.ConsultationStateError, services.ConsultationPermissionError) as exc:
            return _translate(exc)
        return Response(ConsultationSerializer(consultation).data)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        try:
            consultation = services.sign(self.get_object(), by=request.user)
        except (services.ConsultationStateError, services.ConsultationPermissionError) as exc:
            return _translate(exc)
        return Response(ConsultationSerializer(consultation).data)

    @action(detail=True, methods=["post"])
    def amend(self, request, pk=None):
        serializer = AmendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            amendment = services.amend(
                self.get_object(), by=request.user, reason=serializer.validated_data["reason"]
            )
        except (services.ConsultationStateError, services.ConsultationPermissionError) as exc:
            return _translate(exc)
        return Response(
            ConsultationSerializer(amendment).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def diagnoses(self, request, pk=None):
        serializer = AddDiagnosisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = services.add_diagnosis(
                self.get_object(), by=request.user, **serializer.validated_data
            )
        except (services.ConsultationStateError, services.ConsultationPermissionError) as exc:
            return _translate(exc)
        return Response(
            ConsultationDiagnosisSerializer(item).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["delete"], url_path=r"diagnoses/(?P<item_pk>\d+)")
    def remove_diagnosis(self, request, pk=None, item_pk=None):
        try:
            services.remove_diagnosis(self.get_object(), by=request.user, item_pk=item_pk)
        except (services.ConsultationStateError, services.ConsultationPermissionError) as exc:
            return _translate(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)
