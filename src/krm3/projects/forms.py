import datetime
import random
import typing

from django.core.exceptions import ValidationError
from django.forms import CharField, ModelForm, TextInput

from krm3.core.models.projects import Project, Task
from krm3.utils.dates import DATE_INFINITE

if typing.TYPE_CHECKING:
    from krm3.core.models.projects import Resource

def _pick_random_color(*args, **kwargs) -> str:
    return random.choice(  # noqa: S311
        ['ED9B9B', '9E6B6B', 'DECECE', '9A85A8', '769DC6', '315F90', '318F90', '2ADCDF', 'B2ECA2', 'D1E2AB']
    )


class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'client', 'start_date', 'end_date', 'metadata', 'notes']

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['start_date'].initial = datetime.date.today()


class TaskForm(ModelForm):
    color = CharField(
        label='Choose a color',
        widget=TextInput(attrs={'type': 'color', 'value': '#333333'}),
        initial=_pick_random_color,  # Set your default color hex code here
    )

    def clean(self) -> dict:
        """Check that the task has a period-wise matching Contract and does not leave orphan TimeEntries."""
        ret = super().clean()
        task_start_date = ret.get('start_date')
        task_end_date = ret.get('end_date')

        if self.instance and self.instance.pk:
            self._check_orphan_time_entries(task_start_date, task_end_date)

        if (resource := ret.get('resource')) and task_start_date:
            self._check_missing_contracts(resource, task_start_date, task_end_date)

        return ret

    def _check_missing_contracts(
        self, resource: "Resource", task_start_date: datetime.date | None, task_end_date: datetime.date | None
    ) -> None:
        """Verify there are contracts matching the task period."""
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
                    return  # we found a valid period
        raise ValidationError('Contract matching task period not found', code='contract-not-found')

    def _check_orphan_time_entries(
        self, task_start_date: datetime.date | None, task_end_date: datetime.date | None
    ) -> None:
        """Verify there are no orphan TimeEntries when changing the period."""
        orphans = sum(
            1
            for te_date in self.instance.time_entries.values_list('date', flat=True)
            if te_date < task_start_date or te_date > (task_end_date or DATE_INFINITE)
        )
        if orphans:
            raise ValidationError(f'Would leave {orphans} orphan time_entries')

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
