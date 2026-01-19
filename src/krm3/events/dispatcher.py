from django.core import exceptions as django_exceptions
from django.conf import settings
from django.utils.module_loading import import_string

from krm3.events import Event


class EventDispatcher:
    """A generic adapter for event-based notification systems."""

    def __init__(self) -> None:
        """Set up the dispatcher.

        Configuration is located in the `EVENTS` Django setting dict,
        with the following mandatory items:

        * `BACKEND`: the absolute dotted path of the backend class;
        * `OPTIONS`: a dict with configuration options for the backend.

        :raises django.core.exceptions.ImproperlyConfigured: when the
            configuration is missing or lacks any of the mandatory items
        :raises ImportError: when the specified backend class cannot be
            found
        """
        try:
            backend_class = import_string(settings.EVENTS['BACKEND'])
            options = settings.EVENTS['OPTIONS']
        except TypeError as e:
            raise django_exceptions.ImproperlyConfigured('Missing event dispatch configuration') from e
        except KeyError as e:
            raise django_exceptions.ImproperlyConfigured(f'Missing event dispatch configuration item: {e}') from e
        except ImportError:
            raise

        self.backend = backend_class(options)

    def send[T](self, event: Event[T]) -> None:
        """Send an `Event` to the configured notification system.

        The actual event processing and dispatch work is done by the
        underlying backend.

        :param event: the event to send.
        """
        self.backend.send(event)
