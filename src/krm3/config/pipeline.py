from django.contrib import messages
from django.shortcuts import redirect

from krm3.core.models import UserProfile


def auth_allowed(backend, details, response, request, *args, **kwargs):
    if not backend.auth_allowed(response, details):
        messages.error(request, 'Please Login with the Organization Account')
        return redirect('login')


def update_user_social_data(strategy, *args, **kwargs):
    response = kwargs['response']
    user = kwargs['user']

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
