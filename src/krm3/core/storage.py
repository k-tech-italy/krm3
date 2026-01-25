"""Custom storage backends for KRM3."""

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from krm3.core.exceptions import PrivateMediaDirectUrlError


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

    Important: Do not use file.url directly with this storage. Instead, use the
    model's URL property (e.g., contract.document_url, expense.image_url) to get
    authenticated URLs that go through Django's permission checks.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize storage with private media settings."""
        kwargs['location'] = settings.PRIVATE_MEDIA_ROOT
        kwargs['base_url'] = settings.PRIVATE_MEDIA_URL
        super().__init__(*args, **kwargs)

    def url(self, name: str) -> str:
        """Raise an error to prevent direct URL access.

        Use model properties (e.g., contract.document_url, expense.image_url)
        instead to get authenticated URLs.
        """
        raise PrivateMediaDirectUrlError(
            'Direct URL access is not supported for private media. '
            'Use the model URL property (e.g., contract.document_url, expense.image_url) instead.'
        )
