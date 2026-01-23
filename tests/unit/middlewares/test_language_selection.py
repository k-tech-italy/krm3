import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.conf import settings
from django.test import RequestFactory
from unittest.mock import Mock

from testutils.factories import ResourceFactory
from krm3.middlewares.language_selection import UserLanguageMiddleware

User = get_user_model()


@pytest.fixture
def user_with_a_language(resource):
    resource.preferred_language = 'es'
    resource.save()

    return resource.user

def add_session_to_request(request):
    """Helper to add session to request"""
    session_middleware = SessionMiddleware(Mock(return_value=Mock()))
    session_middleware.process_request(request)
    request.session.save()



def test_session_language_takes_priority(user_with_a_language):
    """Session language should override profile language"""
    request = RequestFactory().get('/')
    add_session_to_request(request)
    request.user = user_with_a_language

    # Pre-set session language
    request.session[settings.LANGUAGE_COOKIE_NAME] = 'fr'

    UserLanguageMiddleware(request)

    # Should remain 'fr', not change to profile's 'es'
    assert request.session.get(settings.LANGUAGE_COOKIE_NAME) == 'fr'



def test_language_persists_across_requests(user_with_a_language):
    """Language set from profile should persist in session"""
    # First request
    request1 = RequestFactory().get('/')
    add_session_to_request(request1)
    request1.user = user_with_a_language

    UserLanguageMiddleware(request1)

    # Second request with same session
    request2 = RequestFactory().get('/')
    add_session_to_request(request2)
    request2.session = request1.session
    request2.user = user_with_a_language

    # Change profile language
    user_with_a_language.resource.preferred_language = 'de'

    UserLanguageMiddleware(request2)

    # Should still be 'es' from first request, not 'de'
    assert request2.session.get(settings.LANGUAGE_COOKIE_NAME) == 'es'
