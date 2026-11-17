from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Count, DateTimeField, F, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from krm3.core.models import ChatMessage, ChatParticipant, ChatThread

from .registry import record_owner_id

if TYPE_CHECKING:
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Model, QuerySet

    from krm3.core.models import User

_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)


def _join(thread: ChatThread, user_id: int) -> None:
    ChatParticipant.objects.get_or_create(thread=thread, user_id=user_id)


def resolve_record_thread(user: User, record: Model, content_type: ContentType) -> tuple[ChatThread, bool]:
    """Get or create the single thread of `record`; the requester (and the owner, on creation) join it."""
    thread, created = ChatThread.objects.get_or_create(
        kind=ChatThread.Kind.RECORD,
        content_type=content_type,
        object_id=record.pk,
        defaults={'created_by': user},
    )
    if created and (owner_id := record_owner_id(record)):
        _join(thread, owner_id)
    _join(thread, user.pk)
    return thread, created


def get_or_create_direct_thread(user: User, other: User) -> tuple[ChatThread, bool]:
    low, high = sorted((user, other), key=lambda u: u.pk)
    thread, created = ChatThread.objects.get_or_create(
        kind=ChatThread.Kind.DIRECT,
        direct_user_low=low,
        direct_user_high=high,
        defaults={'created_by': user},
    )
    if created:
        _join(thread, low.pk)
        _join(thread, high.pk)
    return thread, created


@transaction.atomic
def post_message(user: User, thread: ChatThread, body: str) -> ChatMessage:
    message = ChatMessage.objects.create(thread=thread, author=user, body=body)
    ChatThread.objects.filter(pk=thread.pk).update(last_message_at=message.created_at)
    _join(thread, user.pk)
    return message


def mark_read(user: User, thread: ChatThread) -> ChatParticipant:
    participant, __ = ChatParticipant.objects.get_or_create(thread=thread, user=user)
    participant.last_read_at = timezone.now()
    participant.save(update_fields=['last_read_at'])
    return participant


def soft_delete_message(user: User, message: ChatMessage) -> None:
    """Idempotent: deleting an already deleted message keeps the original deletion data."""
    if message.deleted_at is None:
        message.deleted_at = timezone.now()
        message.deleted_by = user
        message.save(update_fields=['deleted_at', 'deleted_by'])


def with_unread_count(threads: QuerySet[ChatThread], user: User) -> QuerySet[ChatThread]:
    """Annotate `unread_count`: others' non-deleted messages newer than the user's `last_read_at`."""
    last_read = ChatParticipant.objects.filter(thread=OuterRef('pk'), user=user).values('last_read_at')[:1]
    unread = (
        ChatMessage.objects.filter(
            thread=OuterRef('pk'),
            deleted_at__isnull=True,
            created_at__gt=Coalesce(OuterRef('my_last_read_at'), Value(_EPOCH, output_field=DateTimeField())),
        )
        .exclude(author=user)
        .order_by()
        .values('thread')
        .annotate(count=Count('pk'))
        .values('count')
    )
    return threads.annotate(my_last_read_at=Subquery(last_read)).annotate(unread_count=Coalesce(Subquery(unread), 0))


def inbox(threads: QuerySet[ChatThread], user: User) -> QuerySet[ChatThread]:
    """Restrict accessible `threads` to the ones `user` participates in, most recent first."""
    return with_unread_count(threads.filter(participants__user=user), user).order_by(
        F('last_message_at').desc(nulls_last=True), '-created_at', '-pk'
    )


def last_messages(threads: list[ChatThread]) -> dict[int, ChatMessage]:
    """Return the latest message of each thread, keyed by thread id (one query)."""
    ids = [t.pk for t in threads]
    latest = (
        ChatMessage.objects.filter(thread_id__in=ids)
        .order_by('thread_id', '-created_at', '-pk')
        .distinct('thread_id')
        .select_related('author')
    )
    return {message.thread_id: message for message in latest}
