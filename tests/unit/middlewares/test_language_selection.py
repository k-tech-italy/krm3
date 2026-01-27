from django.contrib.auth import get_user_model
import pytest
from django.test import Client
from django.conf import settings

User = get_user_model()

LANGUAGE_COOKIE_NAME = settings.LANGUAGE_COOKIE_NAME

@pytest.mark.db
def test_preferred_language_persists_across_sessions(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    response = client.get('/')

    session_language = response.cookies.get(LANGUAGE_COOKIE_NAME)
    assert resource.preferred_language == 'pl', "Sanity check, ResourceFactory should be setting this."
    assert session_language.coded_value == 'pl', "Middleware should set the cookie."

    client.logout()
    client.force_login(resource.user)

    post_re_login_response = client.get('/admin/')
    post_re_login_response_session_language = post_re_login_response.cookies.get(LANGUAGE_COOKIE_NAME)
    assert post_re_login_response_session_language.coded_value == 'pl', "Middleware should set the cookie."
    assert "Witaj" in post_re_login_response.content.decode()


@pytest.mark.db
def test_cookie_takes_priority_over_preferred_language(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    client.cookies[LANGUAGE_COOKIE_NAME] = 'fr'

    response = client.get('/admin/')
    session_language = response.cookies.get(LANGUAGE_COOKIE_NAME)

    assert session_language.value == 'fr', "Middleware should set the cookie."
    assert "Bienvenue" in response.content.decode()


@pytest.mark.db
def test_unauthenticated_user_skips_middleware():
    client = Client()

    response = client.get('/', follow=True)
    session_language = response.cookies.get(LANGUAGE_COOKIE_NAME)

    assert session_language is None, "No cookie should be set"
