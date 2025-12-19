"""Custom storage backends for KRM3."""

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """Storage backend for private media files served via nginx X-Accel-Redirect.

    Files stored using this backend are not directly accessible via URLs.
    Instead, they are served through Django authorization views that use
    nginx's X-Accel-Redirect feature for efficient file serving.

    This provides:
    - Access control: Files are only accessible to authorized users
    - Performance: nginx handles actual file serving (zero-copy sendfile)
    - Security: Real file paths are never exposed to clients
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize storage with private media root and URL."""
        kwargs['location'] = settings.PRIVATE_MEDIA_ROOT
        kwargs['base_url'] = settings.PRIVATE_MEDIA_URL
        super().__init__(*args, **kwargs)
