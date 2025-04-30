from django.contrib.auth import get_user_model, login as djlogin, logout as djlogout
from rest_framework import mixins, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSetMixin
from rest_framework_simplejwt.tokens import RefreshToken

from krm3.core.api.serializers import UserSerializer
from krm3.core.models import City, Client, Country, Project, Resource

User = get_user_model()


class RefreshTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefreshToken
        fields = '__all__'


class BlacklistRefreshAPIViewSet(ViewSetMixin, GenericAPIView):
    serializer_class = [RefreshTokenSerializer]
    permission_classes = [permissions.IsAuthenticated]

    @action(
        methods=['post'],
        detail=True,
        parser_classes=[JSONParser],
        name='Invalidate refresh token',
    )
    def invalidate(self, request: Request) -> Response:
        """Invalidate the refresh token."""
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response()


class UserAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()

    @action(detail=False, methods=['get'])
    def me(self, request: Request) -> Response:
        serializer = self.get_serializer(request.user)
        return Response(serializer.data | {'_CID_': self.request.META['CSRF_COOKIE']})

    @action(detail=False, methods=['post'])
    def logout(self, request: Request) -> Response:
        # invalidate the session data created from the frontend if any
        djlogout(request)
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request: Request) -> Response:
        user = get_object_or_404(User, username=request.data['username'])
        djlogin(request, user=user, backend='django.contrib.auth.backends.ModelBackend')
        return Response(status=status.HTTP_200_OK)


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'


class ResourceAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ResourceSerializer
    queryset = Resource.objects.all()


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'


class CityAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CitySerializer
    queryset = City.objects.all()


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class CountryAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CountrySerializer
    queryset = Country.objects.all()


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class ProjectAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class ClientAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ClientSerializer
    queryset = Client.objects.all()
