"""Record types that can carry a chat thread.

A model is *chat-capable* when its manager implements `filter_acl(user)` and it declares
`chat_threads = GenericRelation('core.ChatThread')`. Which chat-capable types are actually
enabled is decided at runtime by the constance setting `CHAT_RECORD_CONTENT_TYPES`.

This module must not import models at import time: the constance validator imports it from settings.
"""

from __future__ import annotations

from operator import attrgetter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Model

# "<app_label>.<model>" -> dotted path to the record owner's user id
CHAT_CAPABLE_MODELS: dict[str, str] = {
    'core.mission': 'resource.user_id',
    'core.expense': 'mission.resource.user_id',
    'core.dayentry': 'resource.user_id',
    'core.taskentry': 'day_entry.resource.user_id',
    'core.timesheetsubmission': 'resource.user_id',
}


def parse_content_types(value: str) -> list[str]:
    """Split a comma-separated list of `app_label.model` labels."""
    return [label.strip().lower() for label in (value or '').split(',') if label.strip()]


def content_type_label(content_type: ContentType) -> str:
    return f'{content_type.app_label}.{content_type.model}'


def enabled_content_types() -> dict[str, ContentType]:
    """Return the enabled chat-capable content types, keyed by label.

    Labels in the setting that are not chat-capable are ignored.
    """
    from constance import config  # noqa: PLC0415
    from django.contrib.contenttypes.models import ContentType  # noqa: PLC0415

    return {
        label: ContentType.objects.get_by_natural_key(*label.split('.'))
        for label in parse_content_types(config.CHAT_RECORD_CONTENT_TYPES)
        if label in CHAT_CAPABLE_MODELS
    }


def record_owner_id(obj: Model) -> int | None:
    """Return the id of the user owning a chat-capable record, if any."""
    label = f'{obj._meta.app_label}.{obj._meta.model_name}'
    return attrgetter(CHAT_CAPABLE_MODELS[label])(obj)
