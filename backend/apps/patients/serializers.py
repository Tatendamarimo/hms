from rest_framework import serializers

from .models import Patient, PatientAllergy, PatientCondition

DEMOGRAPHIC_FIELDS = [
    "id", "mrn", "first_name", "last_name", "date_of_birth", "age", "sex",
    "national_id", "phone", "address", "next_of_kin_name", "next_of_kin_phone",
    "blood_group", "medical_aid_provider", "medical_aid_number", "status", "created_at",
]


class PatientSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Patient
        fields = DEMOGRAPHIC_FIELDS
        read_only_fields = ["mrn", "status", "created_at"]


class PatientCreateSerializer(PatientSerializer):
    """Registration requires explicit consent capture (FRD §4.1) and supports
    the audited duplicate override (design §2.1)."""

    consent_confirmed = serializers.BooleanField(write_only=True)
    create_anyway = serializers.BooleanField(write_only=True, default=False)

    class Meta(PatientSerializer.Meta):
        fields = [*DEMOGRAPHIC_FIELDS, "consent_confirmed", "create_anyway"]

    def validate_consent_confirmed(self, value):
        if value is not True:
            raise serializers.ValidationError(
                "Patient consent must be captured before registration."
            )
        return value


class PatientAllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAllergy
        fields = ["id", "substance", "reaction", "severity", "notes", "created_at"]


class PatientConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientCondition
        fields = ["id", "condition", "notes", "created_at"]


class PatientSummarySerializer(serializers.ModelSerializer):
    """Clinical banner payload: who + what must never be missed (design §4)."""

    age = serializers.IntegerField(read_only=True)
    allergies = PatientAllergySerializer(many=True, read_only=True)
    conditions = PatientConditionSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id", "mrn", "first_name", "last_name", "date_of_birth", "age", "sex",
            "blood_group", "status", "allergies", "conditions",
        ]
