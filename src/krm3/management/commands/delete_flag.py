"""Delete a condition from a django-flags feature flag."""

from __future__ import annotations

import djclick as click
from django.core.management import CommandError
from flags.models import FlagState


@click.command()
@click.argument('flag_name')
@click.argument('condition')
@click.argument('value')
def command(flag_name: str, condition: str, value: str) -> None:
    """Delete the CONDITION with expected VALUE from FLAG_NAME, e.g. `delete_flag MISSIONS_ENABLED boolean True`.

    Only conditions stored in the database are affected; those defined in settings.FLAGS cannot be removed.
    """
    deleted, _ = FlagState.objects.filter(name=flag_name, condition=condition, value=value).delete()
    if not deleted:
        raise CommandError(f'No database condition for {flag_name}: {condition} is {value}')
    click.secho(f'Deleted {flag_name}: {condition} is {value}', fg='green')
