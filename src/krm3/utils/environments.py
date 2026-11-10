"""Helpers to describe the deployment environment (Refs: taiga#715).

The environment value comes from the SENTRY_ENVIRONMENT setting: production
environments show no banner, `local` is displayed in pale orange and any other
non-production value (e.g. INT) in light green.

When the setting is empty it is derived from DEBUG (see `resolve_environment`):
development servers run with DEBUG on and get `local`, while deployments such
as Rancher explicitly set DEBUG off (KRM3_DEBUG='0') and get `production`.
Non-production deployments (e.g. INT) set SENTRY_ENVIRONMENT explicitly.
"""

PROD_ENVIRONMENTS = frozenset({'production', 'prod'})

LOCAL_ENVIRONMENT = 'local'

PRODUCTION_ENVIRONMENT = 'production'

# Pale orange for local development.
LOCAL_COLOUR = '#fed7aa'

# Light green for any non-production environment (e.g. INT).
NON_PROD_COLOUR = '#86efac'


def resolve_environment(explicit: str | None, debug: bool) -> str:
    """Return an explicit environment (e.g. INT) when given, otherwise derive it from DEBUG."""
    explicit = (explicit or '').strip()
    if explicit:
        return explicit
    return LOCAL_ENVIRONMENT if debug else PRODUCTION_ENVIRONMENT


def environment_info(environment: str | None) -> dict[str, str | bool]:
    """Describe how the environment banner must be rendered for `environment`."""
    environment = (environment or '').strip().lower()
    if not environment or environment in PROD_ENVIRONMENTS:
        return {'environment': environment, 'show_banner': False, 'label': '', 'color': ''}
    if environment == LOCAL_ENVIRONMENT:
        label, color = 'LOCAL', LOCAL_COLOUR
    else:
        label, color = environment.upper(), NON_PROD_COLOUR
    return {'environment': environment, 'show_banner': True, 'label': label, 'color': color}
