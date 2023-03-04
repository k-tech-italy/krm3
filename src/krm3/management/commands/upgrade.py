from pathlib import Path

import djclick as click
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.validators import validate_email
from django.db import IntegrityError

from krm3.config.environ import env
from krm3.sentry import capture_exception

User = get_user_model()


def configure_dirs(prompt, verbosity):
    for _dir in ('MEDIA_ROOT', 'STATIC_ROOT'):
        target = Path(env.str(_dir))
        if not target.exists():
            if prompt:
                ok = click.prompt(f"{_dir} set to '{target}' but it does not exists. Create it now?")
            else:
                ok = True
            if ok:
                if verbosity > 0:
                    click.echo(f"Create {_dir} '{target}'")
                target.mkdir(parents=True)


@click.command()  # noqa: C901
@click.option('--prompt/--no-input', default=True, is_flag=True,
              help='Do not prompt for parameters')
@click.option('--migrate/--no-migrate', default=True, is_flag=True,
              help='Run database migrations')
@click.option('--static/--no-static', default=False, is_flag=True,
              help='Collect static assets')
@click.option('--traceback', '-tb', default=False, is_flag=True,
              help='Raise on exceptions')
@click.option('-v', '--verbosity', count=True, default=0, help='Enables verbosity mode. Use -vv -vvv to increase')
@click.option('--admin-email', '-ae', default=env.str('ADMIN_EMAIL'), help='Do not prompt for parameters')
@click.option('--admin-username', '-au', default=env.str('ADMIN_USERNAME'), help='Do not prompt for parameters')
@click.option('--admin-password', '-ap', default=env.str('ADMIN_PASSWORD'), help='Do not prompt for parameters')
@click.pass_context
def command(ctx, prompt, migrate, static, verbosity,  # noqa: C901
            traceback, admin_username, admin_email, admin_password,  **kwargs):
    """Perform any pending database migrations and upgrades."""
    try:

        extra = {'no_input': prompt,
                 'verbosity': verbosity - 1}

        configure_dirs(prompt, verbosity)

        if static:
            if verbosity == 1:
                click.echo('Run collectstatic')
            call_command('collectstatic', **extra)

        if migrate:
            if verbosity >= 1:
                click.echo('Run migrations')
            call_command('migrate', **extra)

        if admin_email:
            try:
                email = admin_email.strip()
                validate_email(email)
            except ValidationError as e:
                ctx.fail('\n'.join(e.messages))

            admin_password = admin_password.strip()
            if not admin_password:
                ctx.fail('You must provide a password')
            try:
                user = User.objects.create_superuser(admin_username, admin_email, admin_password)
                if verbosity > 0:
                    click.echo(f'Created superuser {user.username}')
            except IntegrityError as e:
                click.secho(f'Unable to create superuser: {e}', fg='yellow')

        for z in ['currencies', 'rates', 'krm3']:
            click.secho(f'Loading tools/zapdata/demo/{z}.yaml')
            call_command('loaddata', f'tools/zapdata/demo/{z}.yaml')

    except Exception as e:
        if traceback:
            raise
        capture_exception(e)
        click.echo(str(e))
        ctx.abort()
