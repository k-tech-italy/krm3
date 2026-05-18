import datetime
import typing

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _l

from krm3.core.models import Contract, ProtectedDocument, DayEntry
from krm3.core.widgets import PrivateMediaFileInput
from krm3.utils.dates import DATE_INFINITE

if typing.TYPE_CHECKING:
    from krm3.core.models.auth import Resource


class ContractForm(ModelForm):
    working_schedule = forms.JSONField(
        widget=forms.Textarea,
        required=False,
        help_text="""{"mon": 8, "tue": 8, "wed": 8, "thu": 8, "fri": 8, "sat": 0, "sun": 0}""",
    )
    meal_voucher = forms.JSONField(
        widget=forms.Textarea,
        required=False,
        help_text="""{"mon": 6, "tue": 6, "wed": 6, "thu": 6, "fri": 6, "sat": 4, "sun": 4}""",
    )

    def clean_meal_voucher(self) -> typing.Any:
        value = self.cleaned_data['meal_voucher']
        if value in (None, {}):
            return {}
        if set(value) != {'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'}:
            raise ValidationError(_l('Need to specify a value for each day of the week'), code='meal_voucher')
        return value

    def clean_working_schedule(self) -> typing.Any:
        value = self.cleaned_data['working_schedule']
        if value in (None, {}):
            return {}
        if set(value) != {'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'}:
            raise ValidationError(_l('Need to specify a value for each day of the week'), code='meal_voucher')
        return value

    def clean(self) -> dict | None:
        ret = super().clean()
        if self.instance.id and (new_period := self.cleaned_data.get('period')) and (self.cleaned_data.get('resource')):
            old_period = [self.instance.period.lower, self.instance.period.upper or DATE_INFINITE]
            new_period = [new_period.lower, new_period.upper or DATE_INFINITE]

            # check if interval becomes smaller
            if new_period[1] < old_period[1] or new_period[0] > old_period[0]:
                boundaries = self.instance.period_as_tuple()
                if self.instance.dayentry_set.filter(Q(day_lt=boundaries[0]) | Q(day_gte=boundaries[1])).exists():
                    raise ValidationError('Shrinking contract period would leave orphan tasks', code='orphan-tasks')
        return ret

    class Meta:
        model = Contract
        fields = '__all__'  # noqa: DJ007
        widgets = {
            'document': PrivateMediaFileInput(url_field='document_url'),
        }


class ResourceForm(forms.Form):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    preferred_language = forms.ChoiceField(
        choices=settings.LANGUAGES,
        required=False,
        widget=forms.Select(
            attrs={
                'style': 'color: black;',
                'class': 'language-select',
            }
        ),
    )

    def __init__(self, resource: 'Resource', *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.resource = resource

        # Populate initial values from resource object
        self.fields['first_name'].initial = resource.first_name
        self.fields['last_name'].initial = resource.last_name
        self.fields['preferred_language'].initial = resource.preferred_language

    def save(self) -> 'Resource':
        """Save the form data to Resource model."""
        self.resource.first_name = self.cleaned_data['first_name']
        self.resource.last_name = self.cleaned_data['last_name']
        self.resource.preferred_language = self.cleaned_data['preferred_language']
        self.resource.save()
        return self.resource


class ProtectedDocumentForm(ModelForm):
    """Form for ProtectedDocument with custom widget for private media files."""

    class Meta:
        model = ProtectedDocument
        fields = '__all__'  # noqa: DJ007
        widgets = {
            'document': PrivateMediaFileInput(url_field='file_url'),
        }


class ContractTerminationForm(forms.Form):
    termination_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text=_l(
            'Actual end date of the contract. Tasks without end date for this resource will be updated to this date.'
        ),
        label=_l('Contract end date'),
    )
