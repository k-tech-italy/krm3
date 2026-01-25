from dataclasses import dataclass


@dataclass(frozen=True)
class Event[T]:
    """A generic event meant to be sent to a notification system."""

    name: str
    payload: T
