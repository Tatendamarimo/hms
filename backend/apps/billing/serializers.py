from rest_framework import serializers

from .models import CashUp, Invoice, InvoiceItem, Payment, ServiceItem, ServicePrice


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
            "item_type", "discount_reason", "service_item", "created_at",
        ]


class InvoiceItemCreateSerializer(serializers.Serializer):
    """Transport shape only — amounts, permissions, and invoice-state rules
    live in billing.services."""

    item_type = serializers.ChoiceField(
        choices=InvoiceItem.ItemType.choices, default=InvoiceItem.ItemType.SERVICE
    )
    service_item = serializers.PrimaryKeyRelatedField(
        queryset=ServiceItem.objects.all(), required=False, allow_null=True
    )
    quantity = serializers.IntegerField(min_value=1, default=1)
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["item_type"] == InvoiceItem.ItemType.SERVICE:
            if attrs.get("service_item") is None:
                raise serializers.ValidationError(
                    {"service_item": "A catalog service is required for a service line."}
                )
        elif attrs.get("amount") is None:
            raise serializers.ValidationError(
                {"amount": "A discount needs an amount."}
            )
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(source="received_by.get_full_name", read_only=True)
    reversal_of = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "amount", "method", "reference", "receipt_number",
            "received_by_name", "reversal_of", "created_at",
        ]
        read_only_fields = ["receipt_number", "reversal_of", "created_at"]


class CashUpCloseSerializer(serializers.Serializer):
    """Transport shape only — drawer rules live in billing.services."""

    counted_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CashUpSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source="cashier.get_full_name", read_only=True)
    variance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CashUp
        fields = [
            "id", "cashier_name", "period_start", "period_end",
            "expected_total", "counted_total", "variance", "notes", "status",
            "created_at",
        ]


class UnpaidInvoiceSerializer(serializers.Serializer):
    """One outstanding invoice inside the per-patient unpaid view. Reads the
    aggregates annotated by services.unpaid_invoices — no clinical fields
    (desk-tier serializer, design §4)."""

    id = serializers.IntegerField()
    number = serializers.CharField()
    issued_at = serializers.DateTimeField()
    encounter_status = serializers.CharField(source="encounter.status")
    total = serializers.DecimalField(
        max_digits=10, decimal_places=2, source="total_amount"
    )
    paid = serializers.DecimalField(
        max_digits=10, decimal_places=2, source="paid_amount"
    )
    outstanding = serializers.DecimalField(max_digits=10, decimal_places=2)


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
