from rest_framework import serializers

from .models import Consultation, ConsultationDiagnosis, Diagnosis


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


class ConsultationSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    diagnoses = ConsultationDiagnosisSerializer(many=True, read_only=True)
    amended_by_id = serializers.SerializerMethodField()

    class Meta:
        model = Consultation
        fields = [
            "id", "encounter", "doctor_name", "status", "version",
            "amended_from", "amended_by_id", "amendment_reason",
            "presenting_complaint", "clinical_notes", "treatment_plan",
            "diagnoses", "signed_at", "created_at",
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
