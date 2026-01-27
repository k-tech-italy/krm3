import logging

from django.core import exceptions as django_exceptions
from django.conf import settings
from django import test as django_test
import pytest

from krm3.events import Event
from krm3.events.dispatcher import EventDispatcher


@pytest.fixture(autouse=True)
def events_settings():
    settings.EVENTS = {
        'BACKEND': 'krm3.events.backends.NullEventDispatcherBackend',
        'OPTIONS': {},
    }


@pytest.fixture
def no_events_settings():
    settings.EVENTS = None


@pytest.fixture
def empty_events_settings():
    settings.EVENTS = {}


@pytest.fixture
def bogus_events_settings():
    settings.EVENTS = {
        'BACKEND': 'some.non.existing.event.dispatcher.Backend',
        'OPTIONS': {},
    }


class TestEventDispatcherConfigurationErrors:
    def test_raises_without_configuration(self, no_events_settings):
        with pytest.raises(django_exceptions.ImproperlyConfigured, match='Missing event dispatch configuration'):
            EventDispatcher()

    def test_raises_with_empty_configuration(self, empty_events_settings):
        with pytest.raises(
            django_exceptions.ImproperlyConfigured, match="Missing event dispatch configuration item: 'BACKEND'"
        ):
            EventDispatcher()

    @pytest.mark.parametrize('missing_setting', ('BACKEND', 'OPTIONS'))
    def test_raises_when_setting_is_missing(self, missing_setting):
        settings.EVENTS.pop(missing_setting)
        message_pattern = f"Missing event dispatch configuration item: '{missing_setting}'"
        with pytest.raises(django_exceptions.ImproperlyConfigured, match=message_pattern):
            EventDispatcher()

    def test_raises_with_non_existing_backend_class(self, bogus_events_settings):
        with pytest.raises(ImportError):
            EventDispatcher()


class TestEventDispatcher:
    @django_test.override_settings(FLAGS={'EVENTS_ENABLED': [('boolean', True)]})
    def test_forwards_event_to_backend_with_feature_flag_enabled(self, caplog):
        dispatcher = EventDispatcher()
        with caplog.at_level(logging.DEBUG):
            dispatcher.send(Event(name='test', payload='lorem ipsum dolor'))
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.msg == 'Event "test" sent. Payload: lorem ipsum dolor'

    @django_test.override_settings(FLAGS={'EVENTS_ENABLED': [('boolean', False)]})
    def test_swallows_event_with_feature_flag_disabled(self, caplog):
        dispatcher = EventDispatcher()
        with caplog.at_level(logging.DEBUG):
            dispatcher.send(Event(name='test', payload='lorem ipsum dolor'))
        assert not caplog.records
