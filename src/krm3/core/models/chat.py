from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from krm3.core.models import User

CHAT_MESSAGE_MAX_LENGTH = 4000


class ChatThread(models.Model):
    """A discussion thread, either attached to a business record or between two users.

    Access rules live in `krm3.chat.acl`.
    """

    class Kind(models.TextChoices):
        RECORD = 'RECORD', _('Record')
        DIRECT = 'DIRECT', _('Direct')

    kind = models.CharField(max_length=6, choices=Kind)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # DIRECT threads: the two users ordered by id, so each pair maps to one row.
    direct_user_low = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+'
    )
    direct_user_high = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+'
    )

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('content_type', 'object_id'),
                condition=Q(kind='RECORD'),
                name='chat_unique_record_thread',
            ),
            models.UniqueConstraint(
                fields=('direct_user_low', 'direct_user_high'),
                condition=Q(kind='DIRECT'),
                name='chat_unique_direct_thread',
            ),
            models.CheckConstraint(
                condition=Q(direct_user_low__isnull=True) | Q(direct_user_low__lt=F('direct_user_high')),
                name='chat_direct_users_ordered',
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        kind='RECORD',
                        content_type__isnull=False,
                        object_id__isnull=False,
                        direct_user_low__isnull=True,
                        direct_user_high__isnull=True,
                    )
                    | Q(
                        kind='DIRECT',
                        content_type__isnull=True,
                        object_id__isnull=True,
                        direct_user_low__isnull=False,
                        direct_user_high__isnull=False,
                    )
                ),
                name='chat_thread_kind_fields',
            ),
        ]

    def __str__(self) -> str:
        if self.kind == self.Kind.DIRECT:
            return f'DM {self.direct_user_low} - {self.direct_user_high}'
        return f'{self.content_type} #{self.object_id}'

    @property
    def is_direct(self) -> bool:
        return self.kind == self.Kind.DIRECT

    def other_user(self, user: User) -> User | None:
        """Return the counterpart of `user` in a DIRECT thread."""
        if not self.is_direct:
            return None
        return self.direct_user_high if self.direct_user_low_id == user.pk else self.direct_user_low


class ChatParticipant(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='chat_participations')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('thread', 'user'), name='chat_unique_participant')]

    def __str__(self) -> str:
        return f'{self.user} in thread #{self.thread_id}'


class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    body = models.TextField(max_length=CHAT_MESSAGE_MAX_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+'
    )

    class Meta:
        indexes = [models.Index(fields=('thread', 'created_at'), name='chat_message_thread_created')]

    def __str__(self) -> str:
        # Never include the body: DM content must not leak through admin pages (e.g. delete confirmations).
        return f'Message #{self.pk} by {self.author}'

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
