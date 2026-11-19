from __future__ import annotations

from typing import TYPE_CHECKING

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from krm3.core.api.permissions import FeatureFlagEnabled
from krm3.core.models import ChatMessage, ChatThread

from .. import services
from ..acl import accessible_threads, get_accessible_record
from ..registry import enabled_content_types
from .serializers import (
    ChatConfigSerializer,
    ChatMessageCreateSerializer,
    ChatMessageSerializer,
    ChatThreadSerializer,
    DirectThreadCreateSerializer,
    ReadMarkerSerializer,
    ResolveRecordSerializer,
    UnreadSerializer,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.request import Request


class ChatViewMixin:
    permission_classes = [IsAuthenticated, FeatureFlagEnabled]
    feature_flag = 'CHAT_ENABLED'


class ThreadPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class MessagePagination(CursorPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    ordering = ('-created_at', '-id')


class ChatThreadViewSet(ChatViewMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    """Inbox, thread detail, DIRECT creation, record resolution, messages and read marker."""

    serializer_class = ChatThreadSerializer
    pagination_class = ThreadPagination

    def get_queryset(self) -> QuerySet[ChatThread]:
        if getattr(self, 'swagger_fake_view', False):
            return ChatThread.objects.none()
        user = self.request.user
        threads = accessible_threads(user)
        if self.action == 'list':
            threads = services.inbox(threads, user)
        else:
            threads = services.with_unread_count(threads, user)
        return threads.select_related('content_type', 'direct_user_low', 'direct_user_high').prefetch_related(
            'content_object'
        )

    def _serialize_threads(self, threads: list[ChatThread]) -> list:
        context = {**self.get_serializer_context(), 'last_messages': services.last_messages(threads)}
        return ChatThreadSerializer(threads, many=True, context=context).data

    def _thread_response(self, thread: ChatThread, status_code: int = status.HTTP_200_OK) -> Response:
        thread = self.get_queryset().get(pk=thread.pk)
        return Response(self._serialize_threads([thread])[0], status=status_code)

    def list(self, request: Request, *args, **kwargs) -> Response:  # noqa: ANN002, ANN003
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(self._serialize_threads(page))

    def retrieve(self, request: Request, *args, **kwargs) -> Response:  # noqa: ANN002, ANN003
        return Response(self._serialize_threads([self.get_object()])[0])

    @extend_schema(
        request=DirectThreadCreateSerializer, responses={200: ChatThreadSerializer, 201: ChatThreadSerializer}
    )
    def create(self, request: Request) -> Response:
        """Create, or return the existing, DIRECT thread with `userId`."""
        serializer = DirectThreadCreateSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        thread, created = services.get_or_create_direct_thread(request.user, serializer.validated_data['user_id'])
        return self._thread_response(thread, status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(request=ResolveRecordSerializer, responses={200: ChatThreadSerializer, 201: ChatThreadSerializer})
    @action(detail=False, methods=['post'], url_path='resolve-record')
    def resolve_record(self, request: Request) -> Response:
        """Get or create the thread of a record, checking the allow-list and the record ACL."""
        serializer = ResolveRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        label = serializer.validated_data['content_type'].lower()
        content_type = enabled_content_types().get(label)
        if content_type is None:
            raise serializers.ValidationError({'content_type': f'Chat is not enabled for "{label}".'})
        record = get_accessible_record(request.user, label, serializer.validated_data['object_id'])
        if record is None:
            raise NotFound
        thread, created = services.resolve_record_thread(request.user, record, content_type)
        return self._thread_response(thread, status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(methods=['GET'], responses=ChatMessageSerializer(many=True))
    @extend_schema(methods=['POST'], request=ChatMessageCreateSerializer, responses={201: ChatMessageSerializer})
    @action(detail=True, methods=['get', 'post'], pagination_class=MessagePagination)
    def messages(self, request: Request, pk: str | None = None) -> Response:
        thread: ChatThread = self.get_object()
        if request.method == 'POST':
            return self._post_message(request, thread)
        messages = thread.messages.select_related('author')
        page = self.paginate_queryset(messages)
        return self.get_paginated_response(ChatMessageSerializer(page, many=True).data)

    def _post_message(self, request: Request, thread: ChatThread) -> Response:
        serializer = ChatMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if thread.is_direct and not thread.other_user(request.user).is_active:
            raise serializers.ValidationError('The other user is no longer active.')
        message = services.post_message(request.user, thread, serializer.validated_data['body'])
        return Response(ChatMessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=ReadMarkerSerializer)
    @action(detail=True, methods=['post'])
    def read(self, request: Request, pk: str | None = None) -> Response:
        participant = services.mark_read(request.user, self.get_object())
        return Response({'last_read_at': participant.last_read_at})


class ChatMessageViewSet(ChatViewMixin, mixins.DestroyModelMixin, GenericViewSet):
    """Soft delete of own messages."""

    serializer_class = ChatMessageSerializer

    def get_queryset(self) -> QuerySet[ChatMessage]:
        if getattr(self, 'swagger_fake_view', False):
            return ChatMessage.objects.none()
        return ChatMessage.objects.filter(thread__in=accessible_threads(self.request.user))

    def destroy(self, request: Request, *args, **kwargs) -> Response:  # noqa: ANN002, ANN003
        message: ChatMessage = self.get_object()
        if message.author_id != request.user.pk:
            raise PermissionDenied('You can only delete your own messages.')
        services.soft_delete_message(request.user, message)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UnreadView(ChatViewMixin, APIView):
    """Unread message counts for the threads in the user's inbox."""

    @extend_schema(responses=UnreadSerializer)
    def get(self, request: Request) -> Response:
        threads = services.inbox(accessible_threads(request.user), request.user).filter(unread_count__gt=0)
        counts = [{'thread_id': pk, 'count': count} for pk, count in threads.values_list('pk', 'unread_count')]
        return Response({'total': sum(c['count'] for c in counts), 'threads': counts})


class ChatConfigView(ChatViewMixin, APIView):
    """Chat settings the UI needs, e.g. which record types can have a thread."""

    @extend_schema(responses=ChatConfigSerializer)
    def get(self, request: Request) -> Response:
        return Response({'record_content_types': list(enabled_content_types())})
