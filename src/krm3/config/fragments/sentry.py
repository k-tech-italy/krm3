import logging as _logging

from ...utils.environments import resolve_environment
from ..environ import env as _env

# SENTRY & RAVEN
# need to copy in settings because we inject these values in the templates
SENTRY_DSN = _env('SENTRY_DSN')
# An explicit environment (e.g. INT) always wins; otherwise derive it from DEBUG.
# `_env('DEBUG')` is read directly because this fragment loads before settings.DEBUG is set.
SENTRY_ENVIRONMENT = resolve_environment(_env('SENTRY_ENVIRONMENT'), _env('DEBUG'))
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    from ... import __version__
    from ..environ import env as _env

    SENTRY_PROJECT = _env('SENTRY_PROJECT')
    SENTRY_DEBUG = _env('SENTRY_DEBUG')

    sentry_logging = LoggingIntegration(
        level=_logging.INFO,  # Capture info and above as breadcrumbs
        event_level=_logging.ERROR,  # Send errors as events
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style='url'),
            sentry_logging,
        ],
        release=__version__,
        debug=SENTRY_DEBUG,
        environment=SENTRY_ENVIRONMENT,
        send_default_pii=True,
    )
