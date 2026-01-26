from django.contrib.auth import get_user_model
import pytest
from testutils.factories import ResourceFactory
from django.conf import settings

User = get_user_model()


@pytest.mark.db
def test_preferred_language_persists_across_sessions(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    language_cookie_name = settings.LANGUAGE_COOKIE_NAME
    response = client.get('/')

    session_language = response.cookies.get(language_cookie_name)
    assert resource.preferred_language == 'pl', "Sanity check, ResourceFactory should be setting this."
    assert session_language.coded_value == 'pl', "Middleware should set the cookie."

    client.logout()
    client.force_login(resource.user)

    post_re_login_response = client.get('/admin/')
    post_re_login_response_session_language = post_re_login_response.cookies.get(language_cookie_name)
    assert settings.LANGUAGE_CODE == 'en-uk', "Check we are not false-passing by checking default language."
    assert post_re_login_response_session_language.coded_value == 'pl', "Middleware should set the cookie."
    assert "Witaj" in post_re_login_response.content.decode()

