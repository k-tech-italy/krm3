from sentry_sdk import (capture_exception as _capture_exception,  # noqa
                        configure_scope, push_scope,)


def capture_exception(error=None):
    return _capture_exception(error)


def crashlog_process_exception(exception, request=None, message_user=False):
    return _capture_exception(exception)
