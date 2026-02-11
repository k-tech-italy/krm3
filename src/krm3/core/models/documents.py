"""Proxy models for django-simple-dms integration."""

from __future__ import annotations

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
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


@receiver(pre_save, sender=ProtectedDocument)
def delete_old_file_on_change(sender: type[ProtectedDocument], instance: ProtectedDocument, **kwargs: object) -> None:
    """Delete the old file from storage when a document's file is replaced.

    Uses save=False to only delete the file without re-saving the model,
    which is about to be saved with the new file anyway.
    """
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    if old.document and old.document != instance.document:
        old.document.delete(save=False)


@receiver(post_delete, sender=ProtectedDocument)
def delete_document_file(sender: type[ProtectedDocument], instance: ProtectedDocument, **kwargs: object) -> None:
    """Delete the file from storage when a document is deleted.

    Uses save=False to only delete the file without re-saving the model,
    which no longer exists in the database at this point.
    """
    if instance.document:
        instance.document.delete(save=False)
