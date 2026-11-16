import abc
import logging
from typing import override

from krm3.events import Event

logger = logging.getLogger(__name__)


class EventDispatcherBackend(abc.ABC):
    @abc.abstractmethod
    def send[T](self, event: Event[T]) -> None:
        """Process the given `event` and send a notification trigger.

        :param event: the event to send to the target system.
        """
        ...


class NullEventDispatcherBackend(EventDispatcherBackend):
    @override
    def send[T](self, event: Event[T]) -> None:
        logger.info(f'Event "{event.name}" sent. Payload: {event.payload}')
