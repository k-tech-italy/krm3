"""Custom storage backends for KRM3."""

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """Storage backend for private media files protected by Django authentication.

    Files stored with this backend are saved to PRIVATE_MEDIA_ROOT and are only
    accessible through Django views that perform permission checks. Nginx serves
    the files via X-Accel-Redirect after Django authorizes the request.

    Example usage in models:
        document = models.FileField(
            upload_to=some_upload_function,
            storage=PrivateMediaStorage()
        )
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize storage with private media settings."""
        kwargs['location'] = settings.PRIVATE_MEDIA_ROOT
        kwargs['base_url'] = settings.PRIVATE_MEDIA_URL
        super().__init__(*args, **kwargs)
