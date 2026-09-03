from sentry_sdk import capture_exception as _capture_exception, configure_scope, push_scope  # noqa


def capture_exception(error: BaseException | None = None) -> str | None:
    return _capture_exception(error)
