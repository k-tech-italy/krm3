from flags.state import flag_enabled
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsSelfOrReadOnly(BasePermission):
    """Allow users to only modify their own preferred language."""

    def has_object_permission(self, request, view, obj: object) -> bool:  # noqa: ANN001
        if request.method in SAFE_METHODS:
            return True
        return obj == request.user.resource


class FeatureFlagEnabled(BasePermission):
    """Deny access when the django-flags flag named by `view.feature_flag` is disabled.

    Module-level gating must be enforced API-side as well as UI-side (DDR-G-003).
    """

    message = 'This feature is not enabled.'

    def has_permission(self, request, view) -> bool:  # noqa: ANN001
        flag = getattr(view, 'feature_flag', None)
        return flag is None or flag_enabled(flag, request=request)
