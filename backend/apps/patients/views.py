from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts import roles
from apps.core.api import ClinicScopedViewSetMixin, get_active_clinic
from apps.core.models import AuditLog
from apps.core.permissions import RolePermission

from .models import Patient, PatientAllergy, PatientCondition
from .serializers import (
    PatientAllergySerializer,
    PatientConditionSerializer,
    PatientCreateSerializer,
    PatientSerializer,
    PatientSummarySerializer,
)
from .services import find_duplicate_candidates, register_patient

FRONT_DESK = [roles.RECEPTIONIST, roles.NURSE, roles.DOCTOR, roles.CASHIER]
CLINICAL = [roles.NURSE, roles.DOCTOR]


class PatientViewSet(
    ClinicScopedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Registration is search-first: the UI must call `search` before offering
    `create`, and the API backstops that with the duplicate 409 (design §2.1).
    No destroy — patients are never deleted."""

    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [RolePermission]
    role_map = {
        "create": [roles.RECEPTIONIST],
        "list": FRONT_DESK,
        "retrieve": FRONT_DESK,
        "search": FRONT_DESK,
        "update": [roles.RECEPTIONIST],
        "partial_update": [roles.RECEPTIONIST],
        "summary": CLINICAL,
        "allergies": CLINICAL,
        "void_allergy": CLINICAL,
        "conditions": CLINICAL,
        "void_condition": CLINICAL,
    }

    def get_serializer_class(self):
        if self.action == "create":
            return PatientCreateSerializer
        return PatientSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("consent_confirmed")
        create_anyway = data.pop("create_anyway")
        clinic = get_active_clinic(request)

        # Materialize BEFORE creating: the queryset is lazy, and after creation
        # the new patient would match its own identifiers.
        candidates = list(
            find_duplicate_candidates(
                clinic,
                national_id=data.get("national_id", ""),
                phone=data.get("phone", ""),
            )[:5]
        )
        if candidates and not create_anyway:
            return Response(
                {
                    "detail": (
                        "Possible existing patient(s) matched on national ID or phone. "
                        "Open the existing record, or resubmit with create_anyway=true."
                    ),
                    "candidates": PatientSerializer(candidates, many=True).data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        patient = register_patient(clinic=clinic, registered_by=request.user, **data)

        if candidates:
            # The override is a deliberate, attributable decision (design §2.1)
            AuditLog.objects.create(
                user=request.user,
                clinic=clinic,
                action=AuditLog.Action.CREATE,
                model_label="patients.Patient",
                object_pk=str(patient.pk),
                object_repr=str(patient)[:255],
                changes={"duplicate_override": [c.pk for c in candidates]},
            )

        return Response(
            PatientSerializer(patient).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False)
    def search(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])
        matches = self.get_queryset().filter(
            Q(mrn__iexact=query)
            | Q(national_id__iexact=query)
            | Q(phone__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )[:20]
        return Response(PatientSerializer(matches, many=True).data)

    @action(detail=True)
    def summary(self, request, pk=None):
        patient = self.get_object()
        return Response(PatientSummarySerializer(patient).data)

    # --- Allergies & conditions: add and void only, never edit (design §2.1) ---

    @action(detail=True, methods=["get", "post"])
    def allergies(self, request, pk=None):
        return self._list_or_add(
            request, PatientAllergySerializer, self.get_object().allergies
        )

    @action(detail=True, methods=["post"], url_path=r"allergies/(?P<item_pk>\d+)/void")
    def void_allergy(self, request, pk=None, item_pk=None):
        return self._void(request, PatientAllergy, item_pk)

    @action(detail=True, methods=["get", "post"])
    def conditions(self, request, pk=None):
        return self._list_or_add(
            request, PatientConditionSerializer, self.get_object().conditions
        )

    @action(detail=True, methods=["post"], url_path=r"conditions/(?P<item_pk>\d+)/void")
    def void_condition(self, request, pk=None, item_pk=None):
        return self._void(request, PatientCondition, item_pk)

    def _list_or_add(self, request, serializer_class, related_manager):
        if request.method == "GET":
            return Response(serializer_class(related_manager.all(), many=True).data)
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            patient=self.get_object(),
            clinic=get_active_clinic(request),
            created_by=request.user,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _void(self, request, model, item_pk):
        patient = self.get_object()
        try:
            item = model.objects.get(pk=item_pk, patient=patient)
        except model.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        reason = request.data.get("reason", "")
        try:
            item.void(by=request.user, reason=reason)
        except ValueError as exc:
            return Response({"reason": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
