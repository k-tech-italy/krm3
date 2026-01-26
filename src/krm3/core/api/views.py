from typing import cast

from dateutil.relativedelta import relativedelta
from django.contrib.auth import authenticate, login as djlogin, logout as djlogout
from django.db.models import QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework.pagination import PageNumberPagination

import logging
from krm3.core.api.serializers import UserSerializer, ResourceSerializer, ContactSerializer
from krm3.core.models import (
    City,
    Client,
    Country,
    Project,
    Resource,
    User,
    TimesheetSubmission, Contact,
)
from krm3.timesheet.api.serializers import TimesheetSubmissionSerializer
from krm3.utils.dates import dt


class GoogleOAuthView(APIView):
    """
    Custom view to handle Google OAuth2 authentication for the frontend.

    GET: Returns the authorization URL for the OAuth flow
    POST: Completes the OAuth flow and logs the user in via session
    """

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request: Request, backend: str) -> Response:
        """
        Get the Google OAuth2 authorization URL.

        Frontend calls this with: GET /api/v1/o/google-oauth2/?redirect_uri=http://localhost:8000/login
        """
        from social_django.utils import load_backend, load_strategy
        import base64
        import json

        # Get the frontend redirect URI (where Google should redirect after auth)
        redirect_uri = request.query_params.get('redirect_uri')
        if not redirect_uri:
            return Response({'error': 'redirect_uri is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Load the OAuth backend with the frontend redirect URI
        # Google will redirect to this URL with state and code parameters
        strategy = load_strategy(request)
        oauth_backend = load_backend(strategy, backend, redirect_uri=redirect_uri)

        # Store redirect_uri in the state parameter (base64 encoded)
        # This way it survives across page reloads/new sessions
        state_data = {
            'redirect_uri': redirect_uri,
            'state': oauth_backend.state_token()
        }
        encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        request.session['google-oauth2_state'] = encoded_state
        request.session.save()

        # Get the authorization URL from the backend
        auth_url = oauth_backend.auth_url()

        return Response({'authorization_url': auth_url})

    @method_decorator(ensure_csrf_cookie)
    def post(self, request: Request, backend: str) -> Response:
        """
        Complete the OAuth2 flow and log the user in via session.

        Frontend sends: POST /api/v1/o/google-oauth2/ with state and code in the body
        """
        from social_django.utils import load_backend, load_strategy
        import base64
        import json

        # Get the state from the request (this is our base64-encoded state)
        encoded_state = request.data.get('state') or request.POST.get('state')
        if not encoded_state:
            return Response(
                {'error': 'State parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Decode the state to get the redirect_uri and original OAuth state
        try:
            state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode())
            redirect_uri = state_data.get('redirect_uri')
            state_data.get('state')
        except Exception:
            logging.exception("Failed to decode OAuth state parameter.")
            return Response(
                {'error': 'Failed to decode state.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify against stored state in session
        stored_state = request.session.get('google-oauth2_state')
        if stored_state and stored_state != encoded_state:
            return Response(
                {'error': 'State mismatch. Possible CSRF attack.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Load the OAuth backend with the SAME redirect URI we used in GET
        # This is critical - Google requires the redirect_uri to match exactly
        strategy = load_strategy(request)
        oauth_backend = load_backend(strategy, backend, redirect_uri=redirect_uri)

        # Get the user from the OAuth flow
        # Pass user=None to allow login with already-associated accounts
        user = oauth_backend.complete(user=None)

        if user and user.is_authenticated:
            # Log the user in via Django session
            djlogin(request, user, backend='social_core.backends.google.GoogleOAuth2')

            # Clean up the state from session
            if 'google-oauth2_state' in request.session:
                del request.session['google-oauth2_state']
                request.session.save()

            return Response({
                'detail': 'Login successful',
                'user': UserSerializer(user, context={'request': request}).data
            })

        return Response({'error': 'Authentication failed'}, status=status.HTTP_401_UNAUTHORIZED)


class LoginSerializer(serializers.Serializer):
    """Serializer for username/password login."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class LoginView(APIView):
    """
    Session-based login with username and password.

    POST: Authenticates user and creates a session
    """

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def post(self, request: Request) -> Response:
        """
        Authenticate user with username/password and log them in via session.

        Frontend sends: POST /api/v1/auth/login/ with {username, password}
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        # Authenticate the user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Log the user in via Django session
            djlogin(request, user)

            return Response({
                'detail': 'Login successful',
                'user': UserSerializer(user, context={'request': request}).data
            })

        return Response(
            {'detail': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )


class UserAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()

    @action(detail=False, methods=['get'])
    def me(self, request: Request) -> Response:
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

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create a new Timesheet submission or replace an existing opened one."""
        period = request.data['period'][:]
        period[1] = (dt(period[1]) + relativedelta(days=1)).strftime('%Y-%m-%d')
        ts = TimesheetSubmission.objects.filter(
            resource_id=request.data['resource'], period=period, closed=False
        ).first()
        if ts:
            ts.delete()
        return super().create(request, *args, **kwargs)

class ContactPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20

class ContactAPIViewSet(ReadOnlyModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ContactPagination

    def get_queryset(self) -> QuerySet[Contact]:
        if self.request.user.is_superuser or self.request.user.has_perm('core.view_contact'):
            queryset = Contact.objects.all()
        else:
            queryset = Contact.objects.filter(user=self.request.user)

        active = self.request.query_params.get('active')
        if active:
            queryset = queryset.filter(is_active=True)

        return queryset
