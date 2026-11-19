"""Access rules for chat threads, shared by the REST API and future realtime transports.

* RECORD threads: whoever can see the record through `Model.objects.filter_acl(user)` can read and post
  (owner, `view_any_*`, `manage_any_*`, superusers), provided the record type is enabled in
  `CHAT_RECORD_CONTENT_TYPES`. Checked live on every call.
* DIRECT threads: only the two users of the pair, superusers included.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from krm3.core.models import ChatThread

from .registry import enabled_content_types

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet

    from krm3.core.models import User


def accessible_threads(user: User) -> QuerySet[ChatThread]:
    """Return every thread `user` can read and post to."""
    query = Q(kind=ChatThread.Kind.DIRECT) & (Q(direct_user_low=user) | Q(direct_user_high=user))
    for content_type in enabled_content_types().values():
        records = content_type.model_class().objects.filter_acl(user)
        query |= Q(kind=ChatThread.Kind.RECORD, content_type=content_type, object_id__in=records.values('pk'))
    return ChatThread.objects.filter(query)


def can_access_thread(user: User, thread: ChatThread) -> bool:
    return accessible_threads(user).filter(pk=thread.pk).exists()


def get_accessible_record(user: User, label: str, object_id: int) -> Model | None:
    """Return the record if its type is enabled and `user` can access it, `None` otherwise."""
    content_type = enabled_content_types().get(label)
    if content_type is None:
        return None
    return content_type.model_class().objects.filter_acl(user).filter(pk=object_id).first()
