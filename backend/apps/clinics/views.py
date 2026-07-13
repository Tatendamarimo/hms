from rest_framework import generics

from .models import Clinic
from .serializers import ClinicSerializer


class MyClinicsView(generics.ListAPIView):
    """Clinics the current user can work in (drives the clinic switcher)."""

    serializer_class = ClinicSerializer
    pagination_class = None

    def get_queryset(self):
        return Clinic.objects.filter(
            is_active=True,
            memberships__user=self.request.user,
            memberships__is_active=True,
        ).distinct()
