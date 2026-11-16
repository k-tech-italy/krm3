from unittest import mock

from django import test as django_test

from krm3.events import Event
from krm3.events.dispatcher import EventDispatcher


@django_test.override_settings(FLAGS={'EVENTS_ENABLED': [('boolean', True)]})
def test_sends_event_through_bitcaster_django(settings, monkeypatch):
    settings.EVENTS = {
        'BACKEND': 'krm3.events.backends.bitcaster.BitcasterBackend',
    }
    client = mock.Mock()
    monkeypatch.setattr('krm3.events.backends.bitcaster.Client', mock.Mock(return_value=client))
    event = Event(name='holidays', payload={'start_date': '2026-10-16', 'end_date': '2026-10-16'})

    EventDispatcher().send(event)

    client.trigger_event.assert_called_once_with(event.name, context=event.payload)
