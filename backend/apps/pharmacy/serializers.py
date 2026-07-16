from rest_framework import serializers

from .models import Medication


class MedicationSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = Medication
        fields = ["id", "name", "strength", "form", "label"]
