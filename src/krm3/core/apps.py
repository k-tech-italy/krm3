from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = 'krm3.core'

    def ready(self) -> None:
        super().ready()

        from . import flags as _  # noqa
        from .api import serializers as _  # noqa

        # Monkey-patch django_simple_dms Document model to use PrivateMediaStorage
        # FIXME: This is a temporary workaround until django_simple_dms supports
        # configurable storage backends. The Document model's FileField cannot be
        # overridden programmatically without modifying the external package.
        # This patch ensures all Document files use the private media storage
        # backend for secure file serving via nginx X-Accel-Redirect.
        from django.urls import reverse
        from django_simple_dms.models import Document
        from krm3.core.storage import PrivateMediaStorage

        Document._meta.get_field('document').storage = PrivateMediaStorage()

        # Add property method to get protected URL for Document files
        # Since we can't use ProtectedFileField with external models, we add
        # a helper property that returns the protected view URL
        def get_protected_url(self: Document) -> str:
            """Get the protected URL for this document's file.

            Returns:
                The URL to the protected Django view that serves this file

            """
            return reverse('protected_document', kwargs={'pk': self.pk})

        Document.protected_url = property(get_protected_url)
