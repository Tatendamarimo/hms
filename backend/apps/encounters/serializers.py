from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.billing.models import ServiceItem
from apps.patients.models import Patient

from .models import Encounter, Vitals


class EncounterSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(read_only=True)
    patient_mrn = serializers.CharField(source="patient.mrn", read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    assigned_doctor_name = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()

    class Meta:
        model = Encounter
        fields = [
            "id", "patient_id", "patient_mrn", "patient_name", "type", "status",
            "arrived_at", "closed_at", "assigned_doctor_name", "notes", "invoice",
        ]

    def get_assigned_doctor_name(self, obj) -> str | None:
        return str(obj.assigned_doctor) if obj.assigned_doctor else None

    def get_invoice(self, obj) -> dict | None:
        try:
            invoice = obj.invoice
        except ObjectDoesNotExist:
            return None
        return {
            "id": invoice.pk,
            "number": invoice.number,
            "total": str(invoice.total),
            "balance": str(invoice.balance),
            "status": invoice.status,
        }


class EncounterCreateSerializer(serializers.Serializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    type = serializers.ChoiceField(
        choices=[Encounter.Type.WALK_IN, Encounter.Type.FOLLOW_UP, Encounter.Type.EMERGENCY],
        default=Encounter.Type.WALK_IN,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    checkin_service = serializers.PrimaryKeyRelatedField(
        queryset=ServiceItem.objects.filter(
            is_active=True, type=ServiceItem.Type.CONSULTATION
        ),
        required=False,
        allow_null=True,
        default=None,
    )


class TransitionSerializer(serializers.Serializer):
    to = serializers.ChoiceField(choices=Encounter.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class VitalsSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Vitals
        fields = [
            "id", "systolic", "diastolic", "pulse", "temperature",
            "weight_kg", "height_cm", "spo2", "symptoms",
            "flags", "applied_ranges", "recorded_by_name", "created_at",
        ]
        read_only_fields = ["flags", "applied_ranges", "created_at"]

    def get_recorded_by_name(self, obj) -> str | None:
        return str(obj.created_by) if obj.created_by else None
