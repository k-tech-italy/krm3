"""Unit tests for custom storage backends."""

import pytest
from django.conf import settings

from krm3.core.exceptions import PrivateMediaDirectUrlError
from krm3.core.storage import PrivateMediaStorage


class TestPrivateMediaStorage:
    """Test cases for PrivateMediaStorage class."""

    def test_storage_initialization_sets_location(self):
        """Test that storage __init__ sets location to PRIVATE_MEDIA_ROOT."""
        storage = PrivateMediaStorage()

        assert storage.location == settings.PRIVATE_MEDIA_ROOT

    def test_storage_initialization_sets_base_url(self):
        """Test that storage __init__ sets base_url to PRIVATE_MEDIA_URL."""
        storage = PrivateMediaStorage()

        assert storage.base_url == settings.PRIVATE_MEDIA_URL

    def test_storage_initialization_with_kwargs(self):
        """Test that storage __init__ correctly overrides location and base_url via kwargs."""
        # Our __init__ should override location and base_url even if passed in kwargs
        storage = PrivateMediaStorage(location='/custom/path', base_url='/custom/url/')

        # Our __init__ forces these to use settings
        assert storage.location == settings.PRIVATE_MEDIA_ROOT
        assert storage.base_url == settings.PRIVATE_MEDIA_URL

    def test_url_raises_private_media_direct_url_error(self):
        """Test that calling url() raises PrivateMediaDirectUrlError."""
        storage = PrivateMediaStorage()

        with pytest.raises(PrivateMediaDirectUrlError):
            storage.url('some_file.pdf')
