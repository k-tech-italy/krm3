import json

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.forms import FileField, HiddenInput

from krm3.config.environ import env
from krm3.currencies.models import Currency

# CURRENCY_CHOICES = [c for c in env('CURRENCY_CHOICES') if c != settings.BASE_CURRENCY]

CURRENCY_CHOICES = env('CURRENCY_CHOICES')


class SelectCurrencyMixin:
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['currency'].queryset = Currency.objects.filter(iso3__in=CURRENCY_CHOICES)


class XeFormMixin:
    net_value = forms.DecimalField(widget=HiddenInput)
    tax_value = forms.DecimalField(widget=HiddenInput)

    def save_model(self, request, obj, form, change):
        if 'owner' in form.changed_data:
            messages.add_message(request, messages.INFO, 'Car has been sold')
        super(XeFormMixin, self).save_model(request, obj, form, change)


# class EntityWidget(s2forms.ModelSelect2Widget):
#     search_fields = [
#         "short_name__icontains",
#         "long_name__icontains",
#     ]


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
