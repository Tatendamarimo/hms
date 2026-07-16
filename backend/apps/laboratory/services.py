"""Lab-order lifecycle. Billing is touched ONLY through billing.services:
ordering appends invoice lines (linked to the order); cancelling voids them.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.billing import services as billing
from apps.billing.models import ServiceItem
from apps.clinical.services import (
    ConsultationStateError,
    require_open_document_window,
)
from apps.core.models import AuditLog

from .models import LabOrder, LabOrderItem

ORDERABLE_TYPES = (ServiceItem.Type.LAB, ServiceItem.Type.IMAGING)


def create_lab_order(consultation, *, by, service_items, instructions="") -> LabOrder:
    require_open_document_window(consultation, by)
    if not service_items:
        raise ValidationError({"service_items": "Select at least one test or scan."})
    if len({service.pk for service in service_items}) != len(service_items):
        raise ValidationError(
            {"service_items": "The same service appears more than once — each "
                              "test can only be ordered once per order."}
        )

    clinic = consultation.clinic
    for service in service_items:
        if service.clinic_id != clinic.pk:
            raise ValidationError({"service_items": "Service belongs to a different clinic."})
        if service.type not in ORDERABLE_TYPES:
            raise ValidationError(
                {"service_items": f"'{service.name}' is not a lab or imaging service."}
            )
        if service.current_price() is None:
            raise ValidationError(
                {"service_items": f"'{service.name}' has no price set — the Admin must "
                                  "add one before it can be ordered."}
            )

    with transaction.atomic():
        order = LabOrder.objects.create(
            clinic=clinic,
            consultation=consultation,
            instructions=instructions,
            created_by=by,
        )
        invoice = billing.ensure_invoice(consultation.encounter, created_by=by)
        for service in service_items:
            LabOrderItem.objects.create(
                clinic=clinic,
                lab_order=order,
                service_item=service,
                price=service.current_price(),
                created_by=by,
            )
            billing.add_service_line(
                invoice, service_item=service, created_by=by, lab_order=order
            )
    return order


def cancel_lab_order(order, *, by, reason: str) -> LabOrder:
    """Cancelling voids the linked invoice lines with the reason. If payment
    already covered them, the surplus shows as a negative balance to settle at
    the desk (refund flows arrive with reversals in slice 7)."""
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": "A cancellation reason is required."})
    if order.consultation.doctor_id != by.pk:
        from apps.clinical.services import ConsultationPermissionError

        raise ConsultationPermissionError("Only the ordering doctor may cancel this order.")
    with transaction.atomic():
        locked = LabOrder.objects.select_for_update().get(pk=order.pk)
        if locked.status != LabOrder.Status.ORDERED:
            raise ConsultationStateError("This order is already cancelled.")
        locked.status = LabOrder.Status.CANCELLED
        locked.save(update_fields=["status", "updated_at"])
        billing.void_lines_for_lab_order(locked, by=by, reason=f"Lab order cancelled: {reason}")
        AuditLog.objects.create(
            user=by,
            clinic=locked.clinic,
            action=AuditLog.Action.UPDATE,
            model_label="laboratory.LabOrder",
            object_pk=str(locked.pk),
            object_repr=str(locked)[:255],
            changes={"cancel_reason": reason},
        )
    return locked
