from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clinics.models import Clinic
from apps.core.api import ACTIVE_CLINIC_SESSION_KEY

from .serializers import LoginSerializer, MeSerializer, SwitchClinicSerializer


def _member_clinics(user):
    return list(
        Clinic.objects.filter(
            is_active=True,
            memberships__user=user,
            memberships__is_active=True,
        ).distinct()
    )


def _me_payload(request):
    clinics = _member_clinics(request.user)
    active_id = request.session.get(ACTIVE_CLINIC_SESSION_KEY)
    active = next((c for c in clinics if c.pk == active_id), None)
    return MeSerializer(
        {
            "id": request.user.pk,
            "username": request.user.username,
            "get_full_name": request.user.get_full_name(),
            "role_names": request.user.role_names,
            "active_clinic": active,
            "clinics": clinics,
        }
    ).data


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfView(APIView):
    """GET this before login so the SPA holds a CSRF cookie."""

    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def get(self, request):
        return Response({"detail": "CSRF cookie set"})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            # Deliberately vague: do not reveal whether the account exists or
            # is locked (django-axes raises PermissionDenied on lockout).
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request, user)
        clinics = _member_clinics(user)
        if len(clinics) == 1:
            request.session[ACTIVE_CLINIC_SESSION_KEY] = clinics[0].pk
        return Response(_me_payload(request))


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."})


class MeView(APIView):
    def get(self, request):
        return Response(_me_payload(request))


class SwitchClinicView(APIView):
    """Sets the active clinic for this session; membership is validated here
    and re-validated by ClinicScopedViewSetMixin on every scoped request."""

    def post(self, request):
        serializer = SwitchClinicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clinic_id = serializer.validated_data["clinic_id"]
        if not any(c.pk == clinic_id for c in _member_clinics(request.user)):
            return Response(
                {"detail": "You are not an active member of that clinic."},
                status=status.HTTP_403_FORBIDDEN,
            )
        request.session[ACTIVE_CLINIC_SESSION_KEY] = clinic_id
        return Response(_me_payload(request))
