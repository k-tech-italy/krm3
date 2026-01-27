from typing import NotRequired, TypedDict, override

from krm3.events import Event
import requests
from django.core import exceptions as django_exceptions

from krm3.events.backends import EventDispatcherBackend


_DEFAULT_REQUEST_TIMEOUT_SECONDS = 10


class _Options(TypedDict):
    """Configuration options for the Bitcaster event dispatch backend.

    All options are mandatory, except when explicitly stated otherwise.
    """

    api_key: str
    """An API key provided by the target Bitcaster instance.

    Required to authenticate event trigger requests.
    """

    url: str
    """The target Bitcaster instance's base URL."""

    organization: str
    """The slug of the target organization set up for KRM3 on Bitcaster."""

    project: str
    """The slug of the target project set up for KRM3 on Bitcaster.

    Has nothing to do with KRM3's `Project`.
    """

    application: str
    """The slug of the target application set up for KRM3 on Bitcaster."""

    timeout_seconds: NotRequired[int]
    """The number of seconds to wait before the request times out.

    Optional, defaults to 10 seconds.
    """


class BitcasterBackend(EventDispatcherBackend):
    @override
    def __init__(self, options: _Options) -> None:
        if not all(bool(value) for value in options.values()):
            raise django_exceptions.ImproperlyConfigured('No empty values allowed in Bitcaster options')

        try:
            self.api_key = options['api_key']
            self.url = options['url']
            self.organization = options['organization']
            self.project = options['project']
            self.application = options['application']
        except KeyError as e:
            raise django_exceptions.ImproperlyConfigured(f'Missing option {e} required by Bitcaster')

        self.timeout_seconds = options.get('timeout_seconds', _DEFAULT_REQUEST_TIMEOUT_SECONDS)

    @override
    def send[T](self, event: Event[T]) -> None:
        payload = {'context': event.payload}
        endpoint = f'{self.url}/api/o/{self.organization}/p/{self.project}/a/{self.application}/e/{event.name}/trigger/'
        headers = {'Authorization': f'Key {self.api_key}'}
        requests.post(endpoint, headers=headers, json=payload, timeout=self.timeout_seconds)
