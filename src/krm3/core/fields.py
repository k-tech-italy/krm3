from __future__ import annotations

from django.db.models.fields.files import FieldFile
from django.db import models
from django.urls import reverse


class DynamicUrlFieldFile(FieldFile):
    """A FieldFile whose URL is resolved dynamically via a named URL pattern.

    Rather than delegating to the storage backend, the URL is built by
    reversing the view name configured on the parent field, using the
    model instance's primary key as the argument.
    """

    field: DynamicUrlFileField

    @property
    def url(self) -> str | None:
        """Return the URL for this file by reversing the field's configured view name.

        Returns None if no view name has been set on the field.
        """
        view_name = self.field.view_name
        if not view_name or not self.name:
            return None
        return reverse(view_name, args=[self.instance.pk])


class DynamicUrlFileField(models.FileField):
    """A FileField that resolves the file URL through a named URL pattern instead of the storage backend.

    Pass ``view_name`` with the dotted URL name to use when generating the
    URL for an uploaded file. The view will receive the model instance's
    primary key as its sole positional argument.

    Example::

        document = DynamicUrlFileField(
            upload_to='contracts/',
            view_name='media-auth:contract-document',
        )
    """

    attr_class = DynamicUrlFieldFile

    def __init__(self, *args, view_name: str | None = None, **kwargs) -> None:
        self.view_name = view_name
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple:  # pragma: no cover
        # Required by Django's migration framework to serialize `view_name` into
        # migration files. Without this, makemigrations would silently drop the
        # custom kwarg. Not worth unit-testing: correctness is only observable
        # by running makemigrations, which is an integration-level concern already
        # covered by Django itself.
        name, path, args, kwargs = super().deconstruct()
        if self.view_name is not None:
            kwargs['view_name'] = self.view_name
        return name, path, args, kwargs
