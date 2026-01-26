"""Proxy models for django-simple-dms integration."""

from __future__ import annotations

from django.urls import reverse
from django_simple_dms.models import Document


class ProtectedDocument(Document):
    """Proxy model for Document with protected media URL support.

    This proxy model adds a file_url property that returns the authenticated
    URL for accessing the document file through the media-auth views.
    """

    class Meta:
        proxy = True
        app_label = 'core'
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    @property
    def file_url(self) -> str | None:
        """Return the authenticated URL for the document file."""
        if self.document:
            return reverse('media-auth:document-file', args=[self.pk])
        return None
