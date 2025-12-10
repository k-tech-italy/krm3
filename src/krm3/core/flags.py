from flags.conditions import register


@register('has group')
def has_group(group_name: str, **kwargs) -> bool:
    """Condition for django-flags that is met if the request.user is in a group.

    The group name is passed as an argument to the condition.
    """
    request = kwargs.get('request')
    if not request or not hasattr(request, 'user'):
        return False

    user = request.user
    if not user.is_authenticated:
        return False

    return user.groups.filter(name=group_name).exists()
