from django.contrib.auth.models import Permission


def add_permissions(user: 'User', permissions: str | list[str]):
    if isinstance(permissions, str):
        permissions = [permissions]
    for permission in permissions:
        app_label, permission = permission.split('.')
        user.user_permissions.add(Permission.objects.get(content_type__app_label=app_label, codename=permission))
