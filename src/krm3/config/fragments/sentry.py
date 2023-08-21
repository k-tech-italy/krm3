import logging

from krm3.config.environ import env as _env

# SENTRY & RAVEN
# need to copy in settings because we inject these values in the templates
SENTRY_DSN = _env('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    import krm3

    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style='url'),
            sentry_logging,
        ],
        release=krm3.__version__,
        debug=_env('SENTRY_DEBUG'),
        environment=_env('SENTRY_ENVIRONMENT'),
        send_default_pii=True
    )
