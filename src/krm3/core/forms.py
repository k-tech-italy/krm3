import datetime
import typing

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from krm3.core.models import Contract
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
        if value is None:
            return {}
        return value

    def clean_working_schedule(self) -> typing.Any:
        value = self.cleaned_data['working_schedule']
        if value is None:
            return {}
        return value

    def clean(self) -> dict | None:
        ret = super().clean()
        if self.instance.id and (new_period := self.cleaned_data.get('period')) and (self.cleaned_data.get('resource')):
            old_period = [self.instance.period.lower, self.instance.period.upper or DATE_INFINITE]
            new_period = [new_period.lower, new_period.upper or DATE_INFINITE]

            # check if interval becomes smaller
            if new_period[1] < old_period[1] or new_period[0] > old_period[0]:
                for task in self.instance.get_tasks():
                    task_period = [task.start_date, task.end_date or DATE_INFINITE]
                    if (new_period[0] > old_period[0] and new_period[0] > task_period[0]) or (
                        new_period[1] < old_period[1] and new_period[1] - datetime.timedelta(days=1) < task_period[1]
                    ):
                        raise ValidationError('Shrinking contract period would leave orphan tasks', code='orphan-tasks')

        return ret

    class Meta:
        model = Contract
        fields = '__all__'  # noqa: DJ007


class ResourceForm(forms.Form):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)

    def __init__(self, resource: 'Resource', *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.resource = resource

        # Populate initial values from resource object
        self.fields['first_name'].initial = resource.first_name
        self.fields['last_name'].initial = resource.last_name

    def save(self) -> 'Resource':
        """Save the form data to Resource model."""
        self.resource.first_name = self.cleaned_data['first_name']
        self.resource.last_name = self.cleaned_data['last_name']
        self.resource.save()

        return self.resource
