import abc
import logging
from typing import TypedDict, override
from krm3.events import Event


class EventDispatcherBackend(abc.ABC):
    @abc.abstractmethod
    def __init__(self, options: dict) -> None:
        """Set up the event dispatching backend with the given `options`.

        Setup details are left to the subclass.

        A `django.core.exceptions.ImproperlyConfigured` exception should
        be raised when options do not meet the backend's requirements.

        :param options: a `dict` with configuration options, taken from
            Django settings.
        """
        ...

    @abc.abstractmethod
    def send[T](self, event: Event[T]) -> None:
        """Process the given `event` and send a notification trigger.

        :param event: the event to send to the target system.
        """
        ...


class _NullEventDispatcherOptions(TypedDict):
    pass


class NullEventDispatcherBackend(EventDispatcherBackend):
    @override
    def __init__(self, _options: _NullEventDispatcherOptions) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    @override
    def send[T](self, event: Event[T]) -> None:
        self.logger.info(f'Event "{event.name}" sent. Payload: {event.payload}')
