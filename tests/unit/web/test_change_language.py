from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.shortcuts import reverse
import pytest
from django.test import Client
from django.conf import settings


User = get_user_model()


@pytest.fixture
def django_client_with_auth_resource(resource, staff_user):
    client = Client()
    resource.user = staff_user
    resource.save()
    client.force_login(resource.user)
    return client


def add_session_to_request(request):
    """Helper to add session to request"""
    session_middleware = SessionMiddleware(Mock(return_value=Mock()))
    session_middleware.process_request(request)
    request.session.save()


@pytest.mark.db
def test_language_change_happy_path(django_client_with_auth_resource, resource):

    assert resource.preferred_language == 'it', "Sanity check, ResourceFactory should be setting this."

    response = django_client_with_auth_resource.post(
        reverse('user_resource', args=[resource.user.id]),
        data={
            'first_name': resource.first_name,
            'last_name': resource.last_name,
            'preferred_language': 'en-uk'
        }
    )

    session_language = response.cookies.get(settings.LANGUAGE_COOKIE_NAME)
    assert session_language.coded_value == 'en-uk', "Check the session cookie has been updated."

    admin_panel_body = django_client_with_auth_resource.get('/admin/').content.decode()
    assert 'Welcome' in admin_panel_body, "Check that the language has been updated."
