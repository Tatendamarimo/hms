from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CLINIC_SETTING_DEFAULTS, Clinic
from .serializers import ClinicSerializer


class PublicBrandingView(APIView):
    """Branding for the login page, before any session exists (slice 10
    white-label). A v1 deployment hosts one clinic (design §2.2) — its name
    and branding ARE the product's public face. With zero or several active
    clinics the response falls back to neutral defaults, so nothing
    tenant-specific leaks from a multi-clinic host."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        clinics = list(Clinic.objects.filter(is_active=True)[:2])
        if len(clinics) == 1:
            clinic = clinics[0]
            return Response({"name": clinic.name, "branding": clinic.branding})
        return Response(
            {"name": "HMS", "branding": dict(CLINIC_SETTING_DEFAULTS["branding"])}
        )


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
