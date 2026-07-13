"""Declarative role-based permissions (Phase 1 design §4).

A view declares:

    role_map = {
        "create": [roles.RECEPTIONIST],
        "list": roles.ALL_ROLES,
        "*": [...],          # fallback for undeclared actions
    }

Deny-by-default: no role_map, or an action absent from it (and no "*"), means
nobody gets in. Admin and superusers get NO implicit access — clinical data
access for Admin goes through break-glass only (FRD §3)."""

from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):
    message = "Your role does not permit this action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        role_map = getattr(view, "role_map", None)
        if role_map is None:
            return False
        action = getattr(view, "action", None) or request.method.lower()
        allowed = role_map.get(action, role_map.get("*"))
        if not allowed:
            return False
        return bool(set(allowed) & set(user.role_names))
