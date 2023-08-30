from django.contrib.auth import get_user_model
from requests import Response
from rest_framework import mixins, permissions, serializers
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ViewSetMixin
from rest_framework_simplejwt.tokens import RefreshToken

from krm3.core.models import City, Project, Resource

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


class UserAPIViewSet(
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        GenericViewSet):
    from krm3.core.api.user_serializer import UserSerializer

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = Resource.objects.all()


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'


class ResourceAPIViewSet(
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ResourceSerializer
    queryset = Resource.objects.all()


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'


class CityAPIViewSet(
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CitySerializer
    queryset = City.objects.all()


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class ProjectAPIViewSet(
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
