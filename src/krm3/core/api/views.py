from django.contrib.auth import get_user_model
from requests import Response
from rest_framework import permissions, serializers
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser
from rest_framework.viewsets import ViewSetMixin
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class RefreshTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefreshToken
        fields = '__all__'


class BlacklistRefreshAPIViewSet(ViewSetMixin, GenericAPIView):
    serializer_class = [RefreshTokenSerializer]
    permission_classes = [permissions.IsAuthenticated]

    @action(methods=['post'], detail=True,
            parser_classes=[JSONParser],
            name='Invalidate refresh token')
    def invalidate(self, request):
        """Invalidate the refresh token."""
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response()
