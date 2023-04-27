import abc
import re
from urllib.parse import urlparse, urlunparse

import sentry_sdk

NO_MATCH = object()


class AbstractMasker(abc.ABC):
    def __init__(self, key, value, config, request):
        self.key = key
        self.value = value
        self.config = config
        self.request = request

    def run(self):
        return self.clean()

    @abc.abstractmethod
    def clean(self):
        """Apply a mask to the given sensitive `value`."""
        ...


class AbstractRegexMasker(AbstractMasker, abc.ABC):
    pattern = '<unknown>'

    def run(self):
        if re.search(self.pattern, self.key):
            return self.clean()
        return NO_MATCH

    @abc.abstractmethod
    def clean(self):
        ...


class BaseUrlMasker(AbstractRegexMasker):
    pattern = '<unknown>'
    url_attr = 'password'

    def clean(self):
        try:
            parsed = urlparse(self.value)
            if sensitive_fragment := getattr(parsed, self.url_attr):
                masked_fragment = sensitive_fragment[:2] + '***' + sensitive_fragment[-2:]
                parsed = parsed._replace(netloc=parsed.netloc.replace(sensitive_fragment, masked_fragment))
                return urlunparse(parsed)
        except RuntimeError as e:
            # no need to handle this, log it to Sentry and move on
            sentry_sdk.capture_exception(e)

        return NO_MATCH
