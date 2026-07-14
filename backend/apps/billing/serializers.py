from rest_framework import serializers

from .models import Invoice, InvoiceItem, Payment, ServiceItem, ServicePrice


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


class InvoiceItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceItem
        fields = [
            "id", "description", "quantity", "unit_price", "line_total",
            "item_type", "service_item", "created_at",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(source="received_by.get_full_name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "amount", "method", "reference", "receipt_number",
            "received_by_name", "created_at",
        ]
        read_only_fields = ["receipt_number", "created_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    paid_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "encounter", "issued_at",
            "total", "paid_total", "balance", "status", "items", "payments",
        ]
