import csv
from pathlib import Path

import djclick as click
from sentry_sdk import capture_exception

from krm3.currencies.models import Currency


@click.command()  # noqa: C901
@click.pass_context
def command(ctx,  **kwargs):
    """Loads currencies."""
    try:
        with (Path(__file__).parent / 'currencies.csv').open(newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                Currency.objects.get_or_create(
                    title=row['Currency'],
                    defaults=dict(
                        symbol=row['Symbol or Abbrev.'],
                        iso3=row['ISO code'],
                        fractional_unit=row['Fractional unit'],
                        base=int(row['Number to basic'])
                    )
                )
    except Exception as e:
        capture_exception(e)
        click.echo(str(e))
        ctx.abort()
        raise
