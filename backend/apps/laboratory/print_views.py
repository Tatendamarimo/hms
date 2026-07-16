from django.shortcuts import get_object_or_404, render

from apps.accounts import roles
from apps.core.audit import log_read
from apps.core.printing import print_view

from .models import LabOrder


@print_view([roles.DOCTOR, roles.LAB_TECHNICIAN])
def lab_request(request, clinic, pk):
    order = get_object_or_404(
        LabOrder.objects.filter(clinic=clinic).select_related(
            "consultation__doctor", "consultation__encounter__patient"
        ).prefetch_related("items__service_item"),
        pk=pk,
    )
    log_read(request.user, order)
    return render(request, "print/lab_request.html", {
        "clinic": clinic,
        "order": order,
        "doctor": order.consultation.doctor,
        "patient": order.consultation.encounter.patient,
    })
