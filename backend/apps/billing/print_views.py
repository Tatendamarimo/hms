from django.shortcuts import get_object_or_404, render

from apps.accounts import roles
from apps.core.printing import print_view

from .models import Invoice, Payment

TILL = [roles.RECEPTIONIST, roles.CASHIER, roles.ADMIN]


@print_view(TILL)
def invoice(request, clinic, pk):
    document = get_object_or_404(
        Invoice.objects.filter(clinic=clinic)
        .select_related("encounter__patient")
        .prefetch_related("items", "payments"),
        pk=pk,
    )
    return render(request, "print/invoice.html", {
        "clinic": clinic,
        "invoice": document,
        "patient": document.encounter.patient,
    })


@print_view(TILL)
def receipt(request, clinic, pk):
    payment = get_object_or_404(
        Payment.objects.filter(clinic=clinic).select_related(
            "invoice__encounter__patient", "received_by"
        ),
        pk=pk,
    )
    return render(request, "print/receipt.html", {
        "clinic": clinic,
        "payment": payment,
        "patient": payment.invoice.encounter.patient,
    })
