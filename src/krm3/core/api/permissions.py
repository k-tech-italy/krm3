from operator import attrgetter

from flags.state import flag_enabled
from rest_framework.permissions import SAFE_METHODS, BasePermission


class ResourceMatch(BasePermission):
    """Check the resource is matching requesting user."""

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


class IsOwnerOrManager(BasePermission):
    """Object-level permission: only the owner or a manager can modify a record.

    Read access is left to the view queryset (`filter_acl`), which also grants it to
    view-only users. Write actions require that `view.owner_field` (a dotted attribute
    path to the owner's user id) matches the request user, or that the user has
    `view.manage_permission`.
    """

    def has_object_permission(self, request, view, obj: object) -> bool:  # noqa: ANN001
        if request.method in SAFE_METHODS:
            return True
        if request.user.has_perm(view.manage_permission):
            return True
        return attrgetter(view.owner_field)(obj) == request.user.pk
