"""Print-view plumbing (design §3): session-authenticated, role-gated,
clinic-scoped, server-rendered HTML pages under /print/ (outside /api/v1/).
Plain Django views — the decorator does what RolePermission does for DRF."""

from functools import wraps

from django.http import HttpResponseForbidden
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied

from .api import get_active_clinic


def print_view(allowed_roles):
    """Wraps a view(request, clinic, *args) with auth + role + clinic checks."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Sign in to print documents.")
            if not set(allowed_roles) & set(request.user.role_names):
                return HttpResponseForbidden("Your role cannot print this document.")
            try:
                clinic = get_active_clinic(request)
            except DRFPermissionDenied as exc:
                return HttpResponseForbidden(str(exc))
            return view_func(request, clinic, *args, **kwargs)

        return wrapper

    return decorator
