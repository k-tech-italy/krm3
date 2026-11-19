"""Chat admin.

DM privacy: the bodies of DIRECT messages are never shown, not even to superusers. Thread admin shows
only who talks to whom and when; the message admin is restricted to RECORD threads.
"""

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from krm3.core.models import ChatMessage, ChatParticipant, ChatThread


class ReadOnlyAdminMixin:
    def has_add_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False


class ChatParticipantInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = ChatParticipant
    fields = ('user', 'joined_at', 'last_read_at')
    readonly_fields = fields
    extra = 0
    can_delete = False


@admin.register(ChatThread)
class ChatThreadAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'kind', 'target', 'participant_list', 'message_count', 'created_at', 'last_message_at')
    list_filter = ('kind', 'content_type')
    list_select_related = ('content_type', 'direct_user_low', 'direct_user_high')
    search_fields = ('direct_user_low__username', 'direct_user_high__username', 'participants__user__username')
    fields = (
        'kind',
        'content_type',
        'object_id',
        'direct_user_low',
        'direct_user_high',
        'created_by',
        'created_at',
        'last_message_at',
    )
    readonly_fields = fields
    inlines = [ChatParticipantInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[ChatThread]:
        return (
            super()
            .get_queryset(request)
            .annotate(message_count=Count('messages', distinct=True))
            .prefetch_related('participants__user')
        )

    @admin.display(description='Target')
    def target(self, obj: ChatThread) -> str:
        return str(obj)

    @admin.display(description='Participants')
    def participant_list(self, obj: ChatThread) -> str:
        return ', '.join(str(p.user) for p in obj.participants.all())

    @admin.display(description='Messages', ordering='message_count')
    def message_count(self, obj: ChatThread) -> int:
        return obj.message_count


@admin.register(ChatMessage)
class ChatMessageAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'thread', 'author', 'short_body', 'created_at', 'deleted_at')
    list_select_related = ('thread__content_type', 'author')
    list_filter = ('thread__content_type',)
    search_fields = ('body', 'author__username')
    fields = ('thread', 'author', 'body', 'created_at', 'deleted_at', 'deleted_by')
    readonly_fields = fields

    def get_queryset(self, request: HttpRequest) -> QuerySet[ChatMessage]:
        return super().get_queryset(request).filter(thread__kind=ChatThread.Kind.RECORD)

    @admin.display(description='Body')
    def short_body(self, obj: ChatMessage) -> str:
        return obj.body if len(obj.body) <= 80 else obj.body[:79] + '…'
