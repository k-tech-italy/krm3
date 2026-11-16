import abc
from typing import Any


class Notification(abc.ABC):
    """Build and dispatch a notification event."""

    @abc.abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> None:
        """Build and dispatch the notification."""
        ...
