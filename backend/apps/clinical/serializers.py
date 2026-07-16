from rest_framework import serializers

from apps.pharmacy.models import Medication

from .models import (
    Consultation,
    ConsultationDiagnosis,
    Diagnosis,
    Prescription,
    PrescriptionItem,
    ReferralLetter,
    SickNote,
)


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = ["id", "code", "name"]


class ConsultationDiagnosisSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="diagnosis.code", read_only=True, default=None)
    name = serializers.CharField(source="diagnosis.name", read_only=True, default=None)

    class Meta:
        model = ConsultationDiagnosis
        fields = ["id", "diagnosis", "code", "name", "free_text"]


class PrescriptionItemSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = PrescriptionItem
        fields = [
            "id", "medication", "medication_note", "display_name",
            "dose", "frequency", "duration_days", "quantity", "instructions",
        ]


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)

    class Meta:
        model = Prescription
        fields = ["id", "consultation", "status", "items", "created_at"]


class PrescriptionItemCreateSerializer(serializers.Serializer):
    medication = serializers.PrimaryKeyRelatedField(
        queryset=Medication.objects.filter(is_active=True), required=False, allow_null=True,
        default=None,
    )
    medication_note = serializers.CharField(required=False, allow_blank=True, default="")
    dose = serializers.CharField(max_length=100)
    frequency = serializers.CharField(max_length=100)
    duration_days = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
    instructions = serializers.CharField(required=False, allow_blank=True, default="")


class PrescriptionCreateSerializer(serializers.Serializer):
    items = PrescriptionItemCreateSerializer(many=True)
    acknowledged_allergy_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )


class SickNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SickNote
        fields = ["id", "consultation", "unfit_from", "unfit_to", "remarks", "created_at"]
        read_only_fields = ["consultation", "created_at"]


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralLetter
        fields = ["id", "consultation", "destination_facility", "reason", "created_at"]
        read_only_fields = ["consultation", "created_at"]


class ConsultationSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    diagnoses = ConsultationDiagnosisSerializer(many=True, read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    sick_notes = SickNoteSerializer(many=True, read_only=True)
    referrals = ReferralSerializer(many=True, read_only=True)
    amended_by_id = serializers.SerializerMethodField()

    class Meta:
        model = Consultation
        fields = [
            "id", "encounter", "doctor_name", "status", "version",
            "amended_from", "amended_by_id", "amendment_reason",
            "presenting_complaint", "clinical_notes", "treatment_plan",
            "diagnoses", "prescriptions", "sick_notes", "referrals",
            "signed_at", "created_at",
        ]
        read_only_fields = [
            "encounter", "status", "version", "amended_from", "amendment_reason",
            "signed_at", "created_at",
        ]

    def get_doctor_name(self, obj) -> str:
        return str(obj.doctor)

    def get_amended_by_id(self, obj) -> int | None:
        amendment = Consultation.all_objects.filter(amended_from=obj).first()
        return amendment.pk if amendment else None


class ConsultationEditSerializer(serializers.Serializer):
    presenting_complaint = serializers.CharField(required=False, allow_blank=True)
    clinical_notes = serializers.CharField(required=False, allow_blank=True)
    treatment_plan = serializers.CharField(required=False, allow_blank=True)


class AddDiagnosisSerializer(serializers.Serializer):
    diagnosis = serializers.PrimaryKeyRelatedField(
        queryset=Diagnosis.objects.filter(is_active=True), required=False, allow_null=True,
        default=None,
    )
    free_text = serializers.CharField(required=False, allow_blank=True, default="")


class AmendSerializer(serializers.Serializer):
    reason = serializers.CharField()
