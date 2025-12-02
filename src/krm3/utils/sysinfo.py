from __future__ import annotations

import logging
import typing

from sentry_sdk import capture_exception

if typing.TYPE_CHECKING:
    from django.http import HttpRequest


NO_MATCH = object()

logger = logging.getLogger(__name__)


def get_commit_info(*args: typing.ParamSpecArgs, **kwargs: typing.ParamSpecKwargs) -> str:
    try:
        from krm3 import git_info  # noqa: PLC0415

        return ', '.join([f'{x}={getattr(git_info, x)}' for x in dir(git_info) if not x.startswith('__')])
    except Exception as e:
        capture_exception(e)
        logger.exception(e)
        return ''


def masker(key: str, value: object, config: dict, request: HttpRequest) -> str:
    maskers = []

    for masker_class in maskers:
        if (masked_value := masker_class(key, value, config, request).run()) != NO_MATCH:
            return masked_value
    return (key, value, config, request)
