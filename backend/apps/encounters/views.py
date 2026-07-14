from django.db.models import Case, IntegerField, Value, When
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import roles
from apps.core.api import ClinicScopedViewSetMixin, get_active_clinic
from apps.core.audit import log_read
from apps.core.permissions import RolePermission
from apps.patients.models import Patient

from . import services
from .models import Encounter, Vitals
from .serializers import (
    EncounterCreateSerializer,
    EncounterSerializer,
    TransitionSerializer,
    VitalsSerializer,
)
from .state_machine import GuardFailed, IllegalTransition, TransitionForbidden

QUEUE_ROLES = [
    roles.RECEPTIONIST, roles.NURSE, roles.DOCTOR, roles.CASHIER,
    roles.LAB_TECHNICIAN, roles.PHARMACIST,
]


class EncounterViewSet(
    ClinicScopedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Encounter.objects.select_related(
        "patient", "assigned_doctor"
    ).prefetch_related("invoice__items", "invoice__payments")
    serializer_class = EncounterSerializer
    permission_classes = [RolePermission]
    role_map = {
        "create": [roles.RECEPTIONIST],
        "list": QUEUE_ROLES,
        "retrieve": QUEUE_ROLES,
        "queue": QUEUE_ROLES,
        "transition": QUEUE_ROLES,  # fine-grained per-edge enforcement in the state machine
        "vitals": [roles.NURSE, roles.DOCTOR],  # POST further restricted to Nurse in-action
        "void_vitals": [roles.NURSE, roles.DOCTOR],
    }

    def create(self, request, *args, **kwargs):
        serializer = EncounterCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        encounter = services.open_encounter(
            clinic=get_active_clinic(request),
            opened_by=request.user,
            **serializer.validated_data,
        )
        return Response(
            EncounterSerializer(encounter).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False)
    def queue(self, request):
        """Live queue: open visits, emergencies first, then arrival order.
        Polled by the frontend every 10s (design §2.2)."""
        statuses = request.query_params.getlist("status") or Encounter.OPEN_STATUSES
        open_visits = (
            self.get_queryset()
            .filter(status__in=statuses)
            .annotate(
                priority=Case(
                    When(type=Encounter.Type.EMERGENCY, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by("priority", "arrived_at")[:100]
        )
        return Response(EncounterSerializer(open_visits, many=True).data)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            encounter = services.transition(
                self.get_object(),
                to=serializer.validated_data["to"],
                user=request.user,
                reason=serializer.validated_data["reason"],
            )
        except IllegalTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except TransitionForbidden as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except GuardFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EncounterSerializer(encounter).data)

    @action(detail=True, methods=["get", "post"])
    def vitals(self, request, pk=None):
        encounter = self.get_object()
        if request.method == "GET":
            log_read(request.user, encounter)  # clinical data — reads are audited
            return Response(
                VitalsSerializer(encounter.vitals.all(), many=True).data
            )

        # Recording is Nurse work (FRD §3); doctors read, they don't enter triage data
        if roles.NURSE not in request.user.role_names:
            return Response(
                {"detail": "Only nurses record vitals."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = VitalsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vitals = services.record_vitals(
            encounter, recorded_by=request.user, **serializer.validated_data
        )
        return Response(VitalsSerializer(vitals).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"vitals/(?P<item_pk>\d+)/void")
    def void_vitals(self, request, pk=None, item_pk=None):
        encounter = self.get_object()
        try:
            vitals = Vitals.objects.get(pk=item_pk, encounter=encounter)
        except Vitals.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            vitals.void(by=request.user, reason=request.data.get("reason", ""))
        except ValueError as exc:
            return Response({"reason": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PatientTimelineView(APIView):
    """Chronological visit history — the patient timeline (design §4).
    Lives in encounters (it renders encounters) so the dependency direction
    stays encounters → patients. Reads of a patient's history are audited."""

    permission_classes = [RolePermission]
    role_map = {"get": [roles.NURSE, roles.DOCTOR]}

    def get(self, request, pk):
        patient = get_object_or_404(
            Patient.objects.filter(clinic=get_active_clinic(request)), pk=pk
        )
        log_read(request.user, patient)
        visits = (
            Encounter.objects.filter(patient=patient)
            .select_related("assigned_doctor", "patient")
            .order_by("-arrived_at")[:100]
        )
        return Response(EncounterSerializer(visits, many=True).data)
