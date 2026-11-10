"""Helpers to describe the deployment environment (Refs: taiga#715).

The environment value comes from the SENTRY_ENVIRONMENT setting: production
environments show no banner, `local` is displayed in pale orange and any other
non-production value (e.g. INT) in light green.
"""

PROD_ENVIRONMENTS = frozenset({'production', 'prod'})

LOCAL_ENVIRONMENT = 'local'

# Pale orange for local development.
LOCAL_COLOUR = '#fed7aa'

# Light green for any non-production environment (e.g. INT).
NON_PROD_COLOUR = '#86efac'


def environment_info(environment: str | None) -> dict[str, str | bool]:
    """Describe how the environment banner must be rendered for `environment`."""
    environment = (environment or '').strip().lower()
    if environment in PROD_ENVIRONMENTS:
        return {'environment': environment, 'show_banner': False, 'label': '', 'color': ''}
    if environment == LOCAL_ENVIRONMENT:
        label, color = 'LOCAL', LOCAL_COLOUR
    else:
        label, color = environment.upper(), NON_PROD_COLOUR
    return {'environment': environment, 'show_banner': True, 'label': label, 'color': color}
