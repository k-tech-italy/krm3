from sentry_sdk import capture_exception as _capture_exception, configure_scope, push_scope  # noqa


def capture_exception(error=None):
    return _capture_exception(error)
