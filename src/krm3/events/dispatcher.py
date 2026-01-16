from django.core import exceptions as django_exceptions
from django.conf import settings
from django.utils.module_loading import import_string

from krm3.events import Event


class EventDispatcher:
    def __init__(self) -> None:
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

    def send(self, event: Event) -> None:
        self.backend.send(event)
