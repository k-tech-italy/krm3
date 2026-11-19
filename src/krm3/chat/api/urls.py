from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ChatConfigView, ChatMessageViewSet, ChatThreadViewSet, UnreadView

router = SimpleRouter()
router.register('threads', ChatThreadViewSet, basename='thread')
router.register('messages', ChatMessageViewSet, basename='message')

urlpatterns = [
    path('unread/', UnreadView.as_view(), name='unread'),
    path('config/', ChatConfigView.as_view(), name='config'),
    *router.urls,
]
