import djclick as click

from krm3.events.notifications.registry import NOTIFICATIONS


@click.command()
def command() -> None:
    """List notifications supported by KRM3."""
    click.echo('Available notifications:')
    for name, notification_class in NOTIFICATIONS.items():
        click.echo(f'- {name}: {notification_class.__name__}')
