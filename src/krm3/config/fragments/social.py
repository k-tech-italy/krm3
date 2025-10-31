"""Debug toolbar settings fragments.

Add SOCIAL_MIDDLEWARES to settings.MIDDLEWARES
"""

import typing

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone

from ..environ import env as _env

if typing.TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
    from social_core.strategy import BaseStrategy
    from social_django.models import UserSocialAuth
    from krm3.core.models.auth import User


AUTHENTICATION_BACKENDS = []
if SOCIAL_AUTH_GOOGLE_OAUTH2_KEY := _env('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY'):
    SOCIAL_MIDDLEWARES = ['social_django.middleware.SocialAuthExceptionMiddleware']

    SOCIAL_TEMPLATE_PROCESSORS = [
        'social_django.context_processors.backends',
        'social_django.context_processors.login_redirect',
    ]

    # Session-based authentication configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = not _env('DEBUG', default=False)  # True in production, False in dev

    SOCIAL_AUTH_JSONFIELD_ENABLED = True

    AUTHENTICATION_BACKENDS += [
        'social_core.backends.google.GoogleOAuth2',
        'social_core.backends.google.GoogleOAuth',
    ]

    SOCIAL_AUTH_PIPELINE = (
        'social_core.pipeline.social_auth.social_details',
        'social_core.pipeline.social_auth.social_uid',
        'social_core.pipeline.social_auth.social_user',
        # 'krm3.config.social.auth_allowed',
        'social_core.pipeline.user.get_username',
        'social_core.pipeline.social_auth.associate_by_email',
        'social_core.pipeline.user.create_user',
        'social_core.pipeline.social_auth.associate_user',
        'social_core.pipeline.social_auth.load_extra_data',
        'social_core.pipeline.user.user_details',
        'krm3.config.fragments.social.update_user_social_data',
        'krm3.config.fragments.social.associate_resource',
        'krm3.config.fragments.social.update_last_login',
    )

    SOCIAL_AUTH_STRATEGY = 'social_django.strategy.DjangoStrategy'
    SOCIAL_AUTH_STORAGE = 'social_django.models.DjangoStorage'
    SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['username', 'first_name', 'email']
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = _env('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')
    SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid',
    ]
    SOCIAL_AUTH_GOOGLE_OAUTH2_EXTRA_DATA = ['first_name', 'last_name']
    SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS = _env('SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS')
    SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {'prompt': 'select_account'}
    SOCIAL_AUTH_FIELDS_STORED_IN_SESSION = ['state']

    # Allow login with already associated accounts
    SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
    SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/'
    SOCIAL_AUTH_RAISE_EXCEPTIONS = False

    def auth_allowed(
        backend: typing.Any, details: typing.Any, response: 'HttpResponse', request: 'HttpRequest', *args, **kwargs
    ) -> 'HttpResponseRedirect | None':
        if not backend.auth_allowed(response, details):
            messages.error(request, 'Please Login with the Organization Account')
            return redirect('login')
        return None

    def update_user_social_data(strategy: 'BaseStrategy', *args, **kwargs) -> None:
        response = kwargs['response']
        user = kwargs['user']

        from ...core.models import UserProfile

        user_profile, _ = UserProfile.objects.get_or_create(user=user)

        modified = False

        if (url := response.get('picture')) and user_profile.picture != url:
            user_profile.picture = url
            modified = True

        if (profile := response.get('profile')) and user_profile.social_profile != profile:
            user_profile.social_profile = profile
            modified = True

        if modified:
            user_profile.save()

    def associate_resource(
        strategy: 'BaseStrategy',
        user: 'User',
        response: dict,
        social: 'UserSocialAuth',
        *args,
        **kwargs,
    ) -> None:
        if not kwargs.get('is_new'):
            return

        from krm3.core.models import Resource

        try:
            resource = Resource.objects.get(
                first_name=user.first_name,
                last_name=user.last_name,
                user__isnull=True,
            )
            resource.user = user
            resource.save()
        except Resource.DoesNotExist:
            pass

    def update_last_login(strategy: 'BaseStrategy', user: 'User', *args, **kwargs) -> None:
        if user:
            user.last_login = timezone.now()
            user.save()
