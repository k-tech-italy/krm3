"""
Integration test for LOCAL_DEVELOPMENT setting controlling static file serving.

This test verifies that when LOCAL_DEVELOPMENT is True, Django serves the frontend
application (static files), and when False, it returns 404 (nginx would serve in production).
"""

import copy
import typing

import pytest
from django.test import override_settings
from django.urls import clear_url_caches

if typing.TYPE_CHECKING:
    from testutils.selenium import AppTestBrowser

pytestmark = [pytest.mark.selenium, pytest.mark.django_db]


@pytest.fixture
def restore_urlpatterns():
    """
    Fixture to save and restore URL patterns after test.
    This ensures that changes to urlpatterns during the test don't affect other tests.
    """
    from krm3.config import urls

    # Save original urlpatterns
    original_urlpatterns = copy.copy(urls.urlpatterns)

    # Yield control to the test
    yield

    # Restore original urlpatterns after test completes (even if test fails)
    urls.urlpatterns = original_urlpatterns
    clear_url_caches()


@override_settings(LOCAL_DEVELOPMENT=True)
@pytest.mark.django_db
def test_static_serve_enabled_with_local_development(browser: 'AppTestBrowser', restore_urlpatterns):
    """
    When LOCAL_DEVELOPMENT=True, navigating to '/' should serve the frontend application.
    The login form should be visible, indicating Django is serving static files.
    """
    # Clear URL caches to reload urlpatterns with new setting
    clear_url_caches()

    # Reload the URL configuration to apply the override_settings
    import importlib
    from krm3.config import urls
    importlib.reload(urls)

    # Navigate to root - this would load the frontend SPA
    browser.open('/')

    # The frontend should load and show the login form
    # Wait for the login form to be present (this means static files are being served)
    browser.wait_for_element_present('input[name="username"]', timeout=5)
    browser.wait_for_element_present('input[name="password"]', timeout=5)

    # Verify we're not getting a 404 or error page
    assert '404' not in browser.get_page_source()
    assert 'Not Found' not in browser.get_title()


@override_settings(LOCAL_DEVELOPMENT=False)
@pytest.mark.django_db
def test_static_serve_disabled_without_local_development(browser: 'AppTestBrowser', restore_urlpatterns):
    """
    When LOCAL_DEVELOPMENT=False, navigating to '/' should return 404.
    In production, nginx serves static files, so Django shouldn't handle this route.
    """
    # Clear URL caches to reload urlpatterns with new setting
    clear_url_caches()

    # Reload the URL configuration to apply the override_settings
    import importlib
    from krm3.config import urls
    importlib.reload(urls)

    # Navigate to root - this should NOT be handled by Django
    browser.open('/')

    # Should get a 404 since fe.urls is not included
    # Django's default 404 page or we check the status
    page_source = browser.get_page_source()

    # Check for 404 indicators (Django's debug 404 page or production 404)
    assert ('404' in page_source or
            'Not Found' in browser.get_title() or
            'Page not found' in page_source), (
        "Should return 404 when LOCAL_DEVELOPMENT=False (production mode)"
    )
