import random

from django.core.exceptions import ValidationError
from django.forms import ModelForm, TextInput, CharField

from krm3.core.models.projects import Task


def _pick_random_color(*args, **kwargs) -> str:
    return random.choice(  # noqa: S311
        ['ED9B9B', '9E6B6B', 'DECECE', '9A85A8', '769DC6', '315F90', '318F90', '2ADCDF', 'B2ECA2', 'D1E2AB']
    )


class TaskForm(ModelForm):
    color = CharField(
        label='Choose a color',
        widget=TextInput(attrs={'type': 'color', 'value': '#333333'}),
        initial=_pick_random_color,  # Set your default color hex code here
    )

    def clean(self) -> dict:
        """Check that the task has a period-wise matching Contract."""
        ret = super().clean()
        if (resource := ret.get('resource')) and (task_start_date := ret.get('start_date')):
            task_end_date = ret.get('end_date')
            overlapping_contracts = list(resource.get_contracts(task_start_date, task_end_date))
            if overlapping_contracts:
                contiguous_periods = [[overlapping_contracts[0].period.lower, overlapping_contracts[0].period.upper]]
                for contract in overlapping_contracts[1:]:
                    if contract.period.lower == contiguous_periods[-1][1]:
                        contiguous_periods[-1][1] = contract.period.upper
                    else:
                        contiguous_periods.append([contract.period.lower, contract.period.upper])
                for period in contiguous_periods:
                    if task_start_date >= period[0] and (
                        period[1] is None or (task_end_date is not None and task_end_date < period[1])
                    ):
                        return None  # we found a valid period
            raise ValidationError('Contract matching task period not found', code='contract-not-found')

        return ret

    def clean_color(self) -> None:
        if self.cleaned_data['color'] == '#000000':
            self.cleaned_data['color'] = None

    class Meta:
        model = Task
        fields = [
            'title',
            'basket_title',
            'project',
            'resource',
            'color',
            'start_date',
            'end_date',
            'work_price',
            'on_call_price',
            'travel_price',
            'overtime_price',
            'project',
            'resource',
        ]
