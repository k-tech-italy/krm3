import logging

from sentry_sdk import capture_exception

NO_MATCH = object()

logger = logging.getLogger(__name__)


def get_commit_info(*args, **kwargs):
    try:
        import krm3.git_info as git_info

        return ', '.join([f'{x}={getattr(git_info, x)}' for x in dir(git_info) if not x.startswith('__')])
    except Exception as e:
        capture_exception(e)
        logger.exception(e)
        return []


def masker(key, value, config, request):
    maskers = []

    for masker_class in maskers:
        if (masked_value := masker_class(key, value, config, request).run()) != NO_MATCH:
            return masked_value
    else:
        cleansed = (key, value, config, request)
        return cleansed
