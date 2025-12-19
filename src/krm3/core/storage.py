"""Custom storage backends for KRM3."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import FileField
from django.urls import reverse

if TYPE_CHECKING:
    from django.db.models import Model
    from django.db.models.fields.files import FieldFile


class ProtectedFileDescriptor:
    """Descriptor that overrides FileField's url property to return protected URLs.

    This descriptor wraps the standard FileField descriptor and intercepts
    the `url` property to return the protected media URL instead of the
    direct file path.
    """

    def __init__(self, field: FileField, url_name: str) -> None:
        """Initialize the descriptor.

        Args:
            field: The FileField instance to wrap
            url_name: The URL name for the protected view (e.g., 'protected_expense')

        """
        self.field = field
        self.url_name = url_name
        self.original_descriptor = field.descriptor_class(field)

    def __get__(self, instance: Model | None, owner: type[Model] | None = None) -> FieldFile | ProtectedFileDescriptor:
        """Get the file field value."""
        if instance is None:
            return self

        # Get the original FieldFile instance
        file = self.original_descriptor.__get__(instance, owner)

        # If there's no file, return the original
        if not file:
            return file

        # Override the url property
        def protected_url() -> str:
            """Generate protected URL for this file."""
            return reverse(self.url_name, kwargs={'pk': instance.pk})

        # Monkey-patch the url property on this specific FieldFile instance
        file.__class__.url = property(lambda self: protected_url())

        return file

    def __set__(self, instance: Model, value: Any) -> None:
        """Set the file field value."""
        self.original_descriptor.__set__(instance, value)


class ProtectedFileField(FileField):
    """FileField that serves files through protected Django views.

    This field overrides the standard FileField to return protected URLs
    instead of direct file paths. The protected URLs point to Django views
    that perform authorization checks before serving files via nginx
    X-Accel-Redirect.

    Usage:
        class MyModel(models.Model):
            document = ProtectedFileField(
                upload_to='documents/',
                storage=PrivateMediaStorage,
                protected_url_name='protected_mymodel',
            )
    """

    def __init__(self, *args: Any, protected_url_name: str, **kwargs: Any) -> None:
        """Initialize the protected file field.

        Args:
            *args: Positional arguments passed to FileField
            protected_url_name: URL name for the protected view
            **kwargs: Keyword arguments passed to FileField

        """
        self.protected_url_name = protected_url_name
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple[str, str, list[Any], dict[str, Any]]:
        """Deconstruct the field for migrations.

        This method is required for Django's migration framework to properly
        serialize the field with its custom protected_url_name argument.
        """
        name, path, args, kwargs = super().deconstruct()
        kwargs['protected_url_name'] = self.protected_url_name
        return name, path, args, kwargs

    def contribute_to_class(self, cls: type[Model], name: str, **kwargs: Any) -> None:
        """Override to use custom descriptor."""
        super().contribute_to_class(cls, name, **kwargs)
        # Replace the descriptor with our protected version
        setattr(cls, self.attname, ProtectedFileDescriptor(self, self.protected_url_name))


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
