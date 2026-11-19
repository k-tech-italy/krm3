from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from krm3.core.models import ChatMessage, ChatThread
from krm3.core.models.chat import CHAT_MESSAGE_MAX_LENGTH

from ..registry import content_type_label

if TYPE_CHECKING:
    from krm3.core.models import User

PREVIEW_LENGTH = 140


class ChatUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, user: User) -> str:
        return user.get_full_name() or user.username


class ChatMessageSerializer(serializers.ModelSerializer):
    author = ChatUserSerializer()
    body = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField()

    class Meta:
        model = ChatMessage
        fields = ('id', 'thread', 'author', 'body', 'is_deleted', 'created_at', 'deleted_at')

    def get_body(self, message: ChatMessage) -> str | None:
        return None if message.is_deleted else message.body


class LastMessageSerializer(ChatMessageSerializer):
    def get_body(self, message: ChatMessage) -> str | None:
        body = super().get_body(message)
        if body and len(body) > PREVIEW_LENGTH:
            return body[: PREVIEW_LENGTH - 1] + '…'
        return body


class ChatThreadSerializer(serializers.ModelSerializer):
    content_type = serializers.SerializerMethodField()
    record_label = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = (
            'id',
            'kind',
            'content_type',
            'object_id',
            'record_label',
            'other_user',
            'created_at',
            'last_message_at',
            'unread_count',
            'last_message',
        )

    def get_content_type(self, thread: ChatThread) -> str | None:
        return content_type_label(thread.content_type) if thread.content_type_id else None

    def get_record_label(self, thread: ChatThread) -> str | None:
        record = thread.content_object if thread.content_type_id else None
        return str(record) if record is not None else None

    def get_other_user(self, thread: ChatThread) -> dict[str, Any] | None:
        other = thread.other_user(self.context['request'].user)
        return ChatUserSerializer(other).data if other else None

    def get_last_message(self, thread: ChatThread) -> dict[str, Any] | None:
        message = self.context.get('last_messages', {}).get(thread.pk)
        return LastMessageSerializer(message).data if message else None


class DirectThreadCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value: int) -> User:
        if value == self.context['request'].user.pk:
            raise serializers.ValidationError('You cannot start a conversation with yourself.')
        other = get_user_model().objects.filter(pk=value, is_active=True).first()
        if other is None:
            raise serializers.ValidationError('User not found or inactive.')
        return other


class ResolveRecordSerializer(serializers.Serializer):
    content_type = serializers.CharField()
    object_id = serializers.IntegerField(min_value=1)


class ChatMessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=CHAT_MESSAGE_MAX_LENGTH, trim_whitespace=True)


class ReadMarkerSerializer(serializers.Serializer):
    last_read_at = serializers.DateTimeField()


class ThreadUnreadSerializer(serializers.Serializer):
    thread_id = serializers.IntegerField()
    count = serializers.IntegerField()


class UnreadSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    threads = ThreadUnreadSerializer(many=True)


class ChatConfigSerializer(serializers.Serializer):
    record_content_types = serializers.ListField(child=serializers.CharField())
