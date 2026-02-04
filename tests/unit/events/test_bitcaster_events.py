import copy
from contextlib import nullcontext as does_not_raise
from unittest import mock

from django.conf import settings
from django.core import exceptions as django_exceptions
from django import test as django_test
from krm3.events import Event
from krm3.events.backends import bitcaster
from krm3.events.dispatcher import EventDispatcher
import pytest


_OPTIONS = {
    'api_key': '2-s3kr17-4u',
    'url': 'https://castme.senp.ai',
    'organization': 'evil-corp',
    'project': 'world-domination',
    'application': 'nyandemic',
    'timeout_seconds': 30,
}
_OPTIONAL_KEYS = ('timeout_seconds',)


@pytest.fixture(autouse=True)
def bitcaster_settings():
    settings.EVENTS = {
        'BACKEND': 'krm3.events.backends.bitcaster.BitcasterBackend',
        'OPTIONS': copy.copy(_OPTIONS),
    }


@pytest.mark.parametrize('missing_option', _OPTIONS.keys())
def test_raises_when_missing_mandatory_option(missing_option):
    settings.EVENTS['OPTIONS'].pop(missing_option)
    expected_to_raise = (
        does_not_raise()
        if missing_option in _OPTIONAL_KEYS
        else pytest.raises(
            django_exceptions.ImproperlyConfigured, match=f"Missing option '{missing_option}' required by Bitcaster"
        )
    )
    with expected_to_raise:
        EventDispatcher()


_MISSING = object()


@django_test.override_settings(FLAGS={'EVENTS_ENABLED': [('boolean', True)]})
@pytest.mark.parametrize('timeout_seconds', (pytest.param(_MISSING, id='default'), pytest.param(420, id='explicit')))
def test_sends_post_request_to_bitcaster_trigger_endpoint(timeout_seconds, monkeypatch):
    """Tests that the dispatcher can handle events correctly.

    The aim of this test is not checking for KRM3-based events
    specifically; rather, it checks that the POST request to the
    Bitcaster API has the correct endpoint, header, payload
    and timeout, so we can allow some silliness :^)
    """
    # ensure we reset the backend's options
    settings.EVENTS['OPTIONS'].pop('timeout_seconds')
    if timeout_seconds is not _MISSING:
        settings.EVENTS['OPTIONS']['timeout_seconds'] = timeout_seconds

    mock_post = mock.Mock()
    monkeypatch.setattr('requests.post', mock_post)

    event_payload = {'passphrase': 'clean the litterbox'}
    event = Event(name='turn-mankind-to-cats', payload=event_payload)
    EventDispatcher().send(event)

    backend_options = settings.EVENTS['OPTIONS']
    expected_endpoint = (
        f'{backend_options["url"]}/api'
        f'/o/{backend_options["organization"]}'
        f'/p/{backend_options["project"]}'
        f'/a/{backend_options["application"]}'
        f'/e/{event.name}/trigger/'
    )
    expected_headers = {'Authorization': f'Key {backend_options["api_key"]}'}
    expected_request_payload = {'context': event_payload}
    expected_timeout_seconds = backend_options.get('timeout_seconds', bitcaster.DEFAULT_REQUEST_TIMEOUT_SECONDS)

    mock_post.assert_called_once_with(
        expected_endpoint, headers=expected_headers, json=expected_request_payload, timeout=expected_timeout_seconds
    )
