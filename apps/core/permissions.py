from rest_framework.permissions import BasePermission


class HasAllPermissions(BasePermission):
    """Allow only if user has ALL codenames listed in view.required_permissions (string or list)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        perms = getattr(view, "required_permissions", None)
        if not perms:
            return True
        if isinstance(perms, str):
            perms = [perms]
        try:
            # Only explicit user permissions (no group permissions)
            effective = set(request.user.get_user_permissions())
            for p in perms:
                if p not in effective:
                    return False
            return True
        except Exception:
            return False


class HasAllRoles(BasePermission):
    """Allow only if user has ALL role names listed in view.required_roles (string or list)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Support method-specific role requirements
        roles = None
        try:
            by_method = getattr(view, "required_roles_by_method", None)
            if by_method and isinstance(by_method, dict):
                roles = by_method.get(request.method.upper())
        except Exception:
            roles = None
        if roles is None:
            roles = getattr(view, "required_roles", None)
        if not roles:
            return True
        if isinstance(roles, str):
            roles = [roles]
        roles = [str(r) for r in roles]
        try:
            user_roles = getattr(request.user, "custom_roles", None)
            if not user_roles:
                return False
            names = set(user_roles.values_list("name", flat=True))
            return all(r in names for r in roles)
        except Exception:
            return False


