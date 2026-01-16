import abc
import logging
from typing import TypedDict, override
from krm3.events import Event


class EventDispatcherBackend(abc.ABC):
    @abc.abstractmethod
    def __init__(self, options: dict) -> None: ...

    @abc.abstractmethod
    def send(self, event: Event) -> None: ...


class _NullEventDispatcherOptions(TypedDict):
    pass


class NullEventDispatcherBackend(EventDispatcherBackend):
    @override
    def __init__(self, _options: _NullEventDispatcherOptions) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    @override
    def send(self, event: Event) -> None:
        self.logger.info(f'Event "{event.name}" sent. Payload: {event.payload}')
