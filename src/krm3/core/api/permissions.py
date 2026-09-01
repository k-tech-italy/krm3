from rest_framework.permissions import SAFE_METHODS, BasePermission

class IsSelfOrReadOnly(BasePermission):
    """Allow users to only modify their own preferred language."""

    def has_object_permission(self, request, view, obj: object) -> bool:  # noqa: ANN001
        if request.method in SAFE_METHODS:
            return True
        return obj == request.user.resource
