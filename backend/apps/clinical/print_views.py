from django.shortcuts import get_object_or_404, render

from apps.accounts import roles
from apps.core.audit import log_read
from apps.core.printing import print_view

from .models import Prescription, ReferralLetter, SickNote


@print_view([roles.DOCTOR])
def prescription(request, clinic, pk):
    document = get_object_or_404(
        Prescription.objects.filter(clinic=clinic).select_related(
            "consultation__doctor", "consultation__encounter__patient"
        ),
        pk=pk,
    )
    log_read(request.user, document)
    return render(request, "print/prescription.html", {
        "clinic": clinic,
        "prescription": document,
        "consultation": document.consultation,
        "doctor": document.consultation.doctor,
        "patient": document.consultation.encounter.patient,
    })


@print_view([roles.DOCTOR])
def sick_note(request, clinic, pk):
    document = get_object_or_404(
        SickNote.objects.filter(clinic=clinic).select_related(
            "consultation__doctor", "consultation__encounter__patient"
        ),
        pk=pk,
    )
    log_read(request.user, document)
    return render(request, "print/sick_note.html", {
        "clinic": clinic,
        "note": document,
        "doctor": document.consultation.doctor,
        "patient": document.consultation.encounter.patient,
    })


@print_view([roles.DOCTOR])
def referral(request, clinic, pk):
    document = get_object_or_404(
        ReferralLetter.objects.filter(clinic=clinic).select_related(
            "consultation__doctor", "consultation__encounter__patient"
        ),
        pk=pk,
    )
    log_read(request.user, document)
    return render(request, "print/referral.html", {
        "clinic": clinic,
        "referral": document,
        "doctor": document.consultation.doctor,
        "patient": document.consultation.encounter.patient,
    })
