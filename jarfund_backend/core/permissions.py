# Custom permissions for views, including ownership checks and wallet authentication
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Read-only is allowed for any request
        if request.method in SAFE_METHODS:
            return True

        # Write requires ownership
        owner = getattr(obj, "owner", None) or getattr(obj, "creator", None)
        return owner == request.user


class IsJarCreator(BasePermission):
    message = "Only the jar creator can perform this action."

    def has_object_permission(self, request, view, obj):
        return obj.creator == request.user


class IsWalletAuthenticated(IsAuthenticated):
    message = "Wallet address not verified. Please connect your MetaMask wallet."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return bool(getattr(request.user, "wallet_address", None))


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
