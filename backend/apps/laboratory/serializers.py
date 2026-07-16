from rest_framework import serializers

from apps.billing.models import ServiceItem

from .models import LabOrder, LabOrderItem


class LabOrderItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="service_item.name", read_only=True)
    type = serializers.CharField(source="service_item.type", read_only=True)

    class Meta:
        model = LabOrderItem
        fields = ["id", "service_item", "name", "type", "price"]


class LabOrderSerializer(serializers.ModelSerializer):
    items = LabOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = LabOrder
        fields = ["id", "consultation", "status", "instructions", "items", "created_at"]


class LabOrderCreateSerializer(serializers.Serializer):
    service_items = serializers.PrimaryKeyRelatedField(
        queryset=ServiceItem.objects.filter(is_active=True), many=True
    )
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
