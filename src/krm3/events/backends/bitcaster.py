from typing import override

from bitcaster_django.client import Client

from krm3.events import Event
from krm3.events.backends import EventDispatcherBackend


class BitcasterBackend(EventDispatcherBackend):
    @override
    def __init__(self) -> None:
        self.client = Client()

    @override
    def send[T](self, event: Event[T]) -> None:
        self.client.trigger_event(event.name, context=event.payload)
