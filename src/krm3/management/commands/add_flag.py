"""Add (or update) a condition on a django-flags feature flag."""

from __future__ import annotations

import djclick as click
from django.core.exceptions import ValidationError
from django.core.management import CommandError
from flags.conditions import get_condition, get_conditions
from flags.models import FlagState
from flags.sources import get_flags


def validate_flag_condition(flag_name: str, condition: str, value: str) -> None:
    """Raise CommandError if the flag is unknown, or the condition or its value is invalid."""
    if flag_name not in get_flags():
        raise CommandError(f'No flag with name {flag_name} exists')
    fn = get_condition(condition)
    if fn is None:
        raise CommandError(f'Unknown condition {condition}. Available: {", ".join(sorted(get_conditions()))}')
    if getattr(fn, 'validate', None) is not None:
        try:
            fn.validate(value)
        except ValidationError as e:
            raise CommandError(f'Invalid value {value!r} for condition {condition}: {"; ".join(e.messages)}') from e


@click.command()
@click.argument('flag_name')
@click.argument('condition')
@click.argument('value')
@click.option('--required', is_flag=True, default=False, help='The condition must be met for the flag to be enabled.')
def command(flag_name: str, condition: str, value: str, required: bool) -> None:
    """Add a CONDITION with expected VALUE to FLAG_NAME, e.g. `add_flag MISSIONS_ENABLED boolean True --required`.

    If the same flag/condition/value already exists, only its `required` attribute is updated.
    """
    validate_flag_condition(flag_name, condition, value)
    _, created = FlagState.objects.update_or_create(
        name=flag_name, condition=condition, value=value, defaults={'required': required}
    )
    click.secho(
        f'{"Added" if created else "Updated"} {flag_name}: {condition} is {value}{" (required)" if required else ""}',
        fg='green',
    )
