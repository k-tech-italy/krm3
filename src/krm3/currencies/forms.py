import json

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import FileField, HiddenInput
from django.http import HttpRequest

from krm3.config.environ import env

CURRENCY_CHOICES = env('CURRENCY_CHOICES')


class XeFormMixin:
    net_value = forms.DecimalField(widget=HiddenInput)
    tax_value = forms.DecimalField(widget=HiddenInput)

    def save_model(
        self, request: HttpRequest, obj: models.Model, form: forms.ModelForm, change: bool
    ) -> None:
        if 'owner' in form.changed_data:
            messages.add_message(request, messages.INFO, 'Car has been sold')
        super().save_model(request, obj, form, change)


class RatesImportForm(forms.Form):
    """Accepts .zip missions dump to import."""

    file = FileField(help_text='Load the missions json file')

    def is_valid(self) -> bool:
        ret = super().is_valid()
        if ret:
            file = self.cleaned_data['file']
            if not file.name.endswith('.json'):
                raise ValidationError('Can only accept .json files')
            try:
                json.loads(file.read())
            except Exception:  # noqa: BLE001
                raise ValidationError('Does not appear to be a valid .json file')
            file.seek(0)
        return ret
