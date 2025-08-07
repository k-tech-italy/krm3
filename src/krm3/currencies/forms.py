import json

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.forms import FileField, HiddenInput

from krm3.config.environ import env

CURRENCY_CHOICES = env('CURRENCY_CHOICES')

class XeFormMixin:
    net_value = forms.DecimalField(widget=HiddenInput)
    tax_value = forms.DecimalField(widget=HiddenInput)

    def save_model(self, request, obj, form, change):
        if 'owner' in form.changed_data:
            messages.add_message(request, messages.INFO, 'Car has been sold')
        super(XeFormMixin, self).save_model(request, obj, form, change)

class RatesImportForm(forms.Form):
    """Accepts .zip missions dump to import."""

    file = FileField(help_text='Load the missions json file')

    def is_valid(self):
        ret = super().is_valid()
        if ret:
            file = self.cleaned_data['file']
            # RateImporter(self.cleaned_data['file']).validate()
            if not file.name.endswith('.json'):
                raise ValidationError('Can only accept .json files')
            try:
                json.loads(file.read())
            except Exception:
                raise ValidationError('Does not appear to be a valid .json file')
            file.seek(0)
        return ret
