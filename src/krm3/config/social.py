from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect

from .environ import env as _env

SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('JWT',),
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

DJOSER = {
    'LOGIN_FIELD': 'email',
    'SOCIAL_AUTH_TOKEN_STRATEGY': 'djoser.social.token.jwt.TokenStrategy',
    'SOCIAL_AUTH_ALLOWED_REDIRECT_URIS': _env.list('SOCIAL_AUTH_ALLOWED_REDIRECT_URIS'),
    'SERIALIZERS': {}
}

SOCIAL_AUTH_JSONFIELD_ENABLED = True

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    'krm3.config.social.auth_allowed',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'krm3.config.social.update_user_social_data',
)

SOCIAL_AUTH_STRATEGY = 'social_django.strategy.DjangoStrategy'
SOCIAL_AUTH_STORAGE = 'social_django.models.DjangoStorage'
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['username', 'first_name', 'email']
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = _env('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = _env('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]
SOCIAL_AUTH_GOOGLE_OAUTH2_EXTRA_DATA = ['first_name', 'last_name']
SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS = ['k-tech.it']
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {'prompt': 'select_account'}


def auth_allowed(backend, details, response, request, *args, **kwargs):
    if not backend.auth_allowed(response, details):
        messages.error(request, 'Please Login with the Organization Account')
        return redirect('login')


def update_user_social_data(strategy, *args, **kwargs):
    response = kwargs['response']
    user = kwargs['user']

    from krm3.core.models import UserProfile
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
