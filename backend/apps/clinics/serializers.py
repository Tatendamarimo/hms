from rest_framework import serializers

from .models import Clinic


class ClinicSerializer(serializers.ModelSerializer):
    branding = serializers.DictField(read_only=True)

    class Meta:
        model = Clinic
        fields = ["id", "name", "code", "address", "phone", "branding"]
