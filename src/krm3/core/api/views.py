from typing import cast
from django.contrib.auth import logout as djlogout
from django.db.models import QuerySet
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.exceptions import TokenError

from krm3.core.api.serializers import UserSerializer, ResourceSerializer
from krm3.core.models import (
    City,
    Client,
    Country,
    Project,
    Resource,
    User,
    TimesheetSubmission,
)
from krm3.timesheet.api.serializers import TimesheetSubmissionSerializer


class InvalidateTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text='Refresh token to blacklist')


class BlacklistRefreshAPIViewSet(GenericViewSet, GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=InvalidateTokenSerializer,
        responses={200: 400},
        description='Blacklist a refresh token',
    )
    @action(
        methods=['post'],
        detail=False,
        parser_classes=[JSONParser],
        name='Blacklist a refresh token',
    )
    def invalidate(self, request: Request) -> Response:
        """Blacklist a refresh token (if exists)."""
        try:
            token = RefreshToken(request.data.get('refresh'))
        except TokenError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        token.blacklist()
        return Response()


class UserAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()

    @action(detail=False, methods=['get'])
    def me(self, request: Request) -> Response:
        if request.headers.get('Authorization') is None:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def logout(self, request: Request) -> Response:
        # invalidate the session data created from the frontend if any
        djlogout(request)
        return Response(status=status.HTTP_200_OK)


class ResourceAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ResourceSerializer
    queryset = Resource.objects.order_by('last_name', 'first_name')

    @action(methods=['get'], detail=False)
    def active(self, request: Request) -> Response:
        user = cast('User', request.user)
        if not user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        active_resources = self.get_queryset().filter(active=True)
        serializer = ResourceSerializer(active_resources, many=True)
        return Response(serializer.data)


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


class TimesheetSubmissionAPIViewSet(viewsets.ModelViewSet):
    queryset = TimesheetSubmission.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TimesheetSubmissionSerializer

    def get_queryset(self) -> QuerySet[TimesheetSubmission]:
        user = cast('User', self.request.user)
        ret = super().get_queryset()
        if not user.has_any_perm('core.manage_any_timesheet', 'core.view_any_timesheet'):
            resource = user.get_resource()
            if resource is None:
                return ret.none()
            ret = ret.filter(resource_id=resource.id)
        return ret
