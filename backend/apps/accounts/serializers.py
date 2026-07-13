from rest_framework import serializers

from apps.clinics.serializers import ClinicSerializer


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False, style={"input_type": "password"})


class SwitchClinicSerializer(serializers.Serializer):
    clinic_id = serializers.IntegerField()


class MeSerializer(serializers.Serializer):
    """Session identity payload for the SPA shell."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField(source="get_full_name")
    roles = serializers.ListField(source="role_names", child=serializers.CharField())
    active_clinic = ClinicSerializer(allow_null=True)
    clinics = ClinicSerializer(many=True)
