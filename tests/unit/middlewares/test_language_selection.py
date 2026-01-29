from django.contrib.auth import get_user_model
import pytest
from django.test import Client
from django.conf import settings
from django.shortcuts import reverse

User = get_user_model()

LANGUAGE_COOKIE_NAME = settings.LANGUAGE_COOKIE_NAME

@pytest.mark.django_db
def test_preferred_language_persists_across_sessions(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    response = client.get('/')

    response_language_cookie = response.cookies.get(LANGUAGE_COOKIE_NAME)
    assert resource.preferred_language == 'pl', "Sanity check, ResourceFactory should be setting this."
    assert response_language_cookie.coded_value == 'pl', "Middleware should set the cookie."

    client.logout()
    client.force_login(resource.user)

    post_re_login_response = client.get(reverse('admin:index'))
    post_re_login_response_language_cookie = post_re_login_response.cookies.get(LANGUAGE_COOKIE_NAME)
    assert post_re_login_response_language_cookie.value == 'pl', "Middleware should set the cookie."
    assert "Witaj" in post_re_login_response.rendered_content


@pytest.mark.django_db
def test_cookie_takes_priority_over_preferred_language(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    response = client.get('/')

    response_language_cookie = response.cookies.get(LANGUAGE_COOKIE_NAME)
    assert resource.preferred_language == 'pl', "Sanity check, ResourceFactory should be setting this."
    assert response_language_cookie.coded_value == 'pl', "Middleware should set the cookie."

    client.post(
        reverse('set_language'),
        data={'language': 'fr'}
    )

    response_french = client.get(reverse('admin:index'))
    assert "Bienvenue" in response_french.rendered_content


@pytest.mark.django_db
def test_unauthenticated_user_skips_middleware():
    client = Client()

    response = client.get('/')
    response_language_cookie = response.cookies.get(LANGUAGE_COOKIE_NAME)

    assert response_language_cookie is None, "No cookie should be set"
