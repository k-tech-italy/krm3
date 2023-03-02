import djclick as click


@click.group()
def group():
    """ Manages demo setup """


@group.command()
@click.pass_context
def setup(ctx, *args, **kwargs):
    """Installs demo data."""
    click.secho('Nothing to do yet', fg='yellow')
