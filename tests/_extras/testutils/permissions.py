import typing

from django.contrib.auth.models import Permission

if typing.TYPE_CHECKING:
    from django.contrib.auth.models import Group
    from krm3.core.models import User


def add_permissions(user: 'User', permissions: str | list[str]):
    if isinstance(permissions, str):
        permissions = [permissions]
    for perm in permissions:
        app_label, permission = perm.split('.')
        user.user_permissions.add(Permission.objects.get(content_type__app_label=app_label, codename=permission))


def add_group_permissions(group: 'Group', permissions: str | list[str]):
    if isinstance(permissions, str):
        permissions = [permissions]
    for perm in permissions:
        app_label, permission = perm.split('.')
        group.permissions.add(Permission.objects.get(content_type__app_label=app_label, codename=permission))
