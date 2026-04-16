"""
Custom DRF permissions for JarFund.
"""
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission:
    - Read (GET, HEAD, OPTIONS) is allowed for anyone.
    - Write (POST, PUT, PATCH, DELETE) requires the request user
      to be the owner of the object.

    The view must pass `obj` to check_object_permissions(), and
    the model must have an `owner` or `creator` attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only is allowed for any request
        if request.method in SAFE_METHODS:
            return True

        # Write requires ownership
        owner = getattr(obj, "owner", None) or getattr(obj, "creator", None)
        return owner == request.user


class IsJarCreator(BasePermission):
    """
    Allow only the creator of a Jar to modify or withdraw it.
    """
    message = "Only the jar creator can perform this action."

    def has_object_permission(self, request, view, obj):
        return obj.creator == request.user


class IsWalletAuthenticated(IsAuthenticated):
    """
    Extends IsAuthenticated with a check that the user
    has a verified wallet address on file.
    """
    message = "Wallet address not verified. Please connect your MetaMask wallet."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return bool(getattr(request.user, "wallet_address", None))


class IsAdminOrReadOnly(BasePermission):
    """
    Allow read access to anyone; write access only to staff/admins.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
