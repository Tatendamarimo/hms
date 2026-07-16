from django.shortcuts import get_object_or_404, render

from apps.accounts import roles
from apps.core.printing import print_view

from .models import Patient


@print_view([roles.RECEPTIONIST])
def registration(request, clinic, pk):
    """Demographics only — deliberately no allergies/conditions on a form
    that gets handed around the front desk (design: printables are role-cut)."""
    patient = get_object_or_404(Patient.objects.filter(clinic=clinic), pk=pk)
    return render(request, "print/registration.html", {"clinic": clinic, "patient": patient})
