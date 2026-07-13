from rest_framework import serializers

from .models import ServiceItem, ServicePrice


class ServiceItemSerializer(serializers.ModelSerializer):
    current_price = serializers.SerializerMethodField()

    class Meta:
        model = ServiceItem
        fields = ["id", "code", "name", "type", "is_active", "current_price"]

    def get_current_price(self, obj) -> str | None:
        price = obj.current_price()
        return str(price) if price is not None else None


class ServicePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePrice
        fields = ["id", "service", "price", "effective_from", "created_at"]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        service = attrs["service"]
        request = self.context["request"]
        from apps.core.api import get_active_clinic

        if service.clinic_id != get_active_clinic(request).pk:
            raise serializers.ValidationError("Service belongs to a different clinic.")
        if ServicePrice.objects.filter(
            service=service, effective_from=attrs["effective_from"]
        ).exists():
            raise serializers.ValidationError(
                "A price for this service with that effective date already exists; "
                "choose a different effective date."
            )
        return attrs
