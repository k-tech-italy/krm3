from django.contrib.auth import get_user_model
import pytest
from testutils.factories import ResourceFactory
from django.conf import settings

User = get_user_model()


@pytest.mark.db
def test_preferred_language_persists_across_sessions(django_client_and_auth_resource):
    client, resource = django_client_and_auth_resource
    response = client.get('/')

    session_language = response.cookies.get(settings.LANGUAGE_COOKIE_NAME)
    assert resource.preferred_language == 'it', "Sanity check, ResourceFactory should be setting this."
    assert session_language.coded_value == 'it', "Middleware should set the cookie."

