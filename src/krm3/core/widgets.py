"""Custom form widgets for KRM3."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from django.utils.html import format_html

if TYPE_CHECKING:
    from typing import Any


class PrivateMediaFileInput(forms.ClearableFileInput):
    """File input widget for private media files.

    This widget is used for FileFields that use PrivateMediaStorage.
    It displays the current file link using a custom URL property from the model
    instead of calling file.url (which raises NotImplementedError for private media).

    Usage in forms:
        class MyForm(forms.ModelForm):
            class Meta:
                model = MyModel
                fields = '__all__'
                widgets = {
                    'document': PrivateMediaFileInput(url_field='document_url'),
                }
    """

    def __init__(self, url_field: str, attrs: dict[str, Any] | None = None) -> None:
        """Initialize widget with the name of the model's URL property.

        Args:
            url_field: Name of the model property that returns the authenticated URL
                       (e.g., 'document_url' for Contract, 'image_url' for Expense)
            attrs: Optional HTML attributes for the widget

        """
        super().__init__(attrs)
        self.url_field = url_field

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        """Get context for rendering, replacing the default URL logic."""
        context = super().get_context(name, value, attrs)

        # Override the URL to use our custom URL field
        if value and hasattr(value, 'instance'):
            # value is a FieldFile, get the model instance
            instance = value.instance
            if hasattr(instance, self.url_field):
                url = getattr(instance, self.url_field)
                if url:
                    context['widget']['value'] = value
                    context['widget']['url'] = url

        return context

    def render(
        self, name: str, value: Any, attrs: dict[str, Any] | None = None, renderer: Any = None
    ) -> str:
        """Render the widget with custom URL handling."""
        if value and hasattr(value, 'instance'):
            instance = value.instance
            if hasattr(instance, self.url_field):
                url = getattr(instance, self.url_field)
                if url:
                    # Render the current file link and the file input
                    current_link = format_html(
                        'Currently: <a href="{}">{}</a><br>',
                        url,
                        value.name.split('/')[-1] if value.name else 'View file',
                    )
                    checkbox_html = ''
                    if not self.is_required:
                        checkbox_name = f'{name}-clear'
                        checkbox_id = f'{name}-clear_id'
                        checkbox_html = format_html(
                            '<input type="checkbox" name="{}" id="{}"> '
                            '<label for="{}">Clear</label><br>',
                            checkbox_name,
                            checkbox_id,
                            checkbox_id,
                        )
                    file_input = super(forms.ClearableFileInput, self).render(
                        name, None, attrs, renderer
                    )
                    return format_html('{}{}Change: {}', current_link, checkbox_html, file_input)

        # No existing file, just render the file input
        return super(forms.ClearableFileInput, self).render(name, value, attrs, renderer)
