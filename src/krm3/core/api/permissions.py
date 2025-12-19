from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSelfOrReadOnly(BasePermission):
    """Allow users to only modify their own preferred language."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj == request.user.resource