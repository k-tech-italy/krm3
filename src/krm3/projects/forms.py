import datetime
import random
import typing

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import CharField, ModelForm, TextInput
from django.utils.translation import gettext_lazy as _
from ktcalendars import KTDateRange

from krm3.core.models.projects import Project, Task

if typing.TYPE_CHECKING:
    from krm3.core.models.projects import Resource


def _pick_random_color(*args, **kwargs) -> str:
    return random.choice(  # noqa: S311
        ['ED9B9B', '9E6B6B', 'DECECE', '9A85A8', '769DC6', '315F90', '318F90', '2ADCDF', 'B2ECA2', 'D1E2AB']
    )


class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'client', 'period', 'metadata', 'notes']

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['period'].initial = (datetime.date.today(), None)

    def save(self, commit: bool = True) -> None:
        return super().save(commit)


class TaskForm(ModelForm):
    color = CharField(
        label='Choose a color',
        widget=TextInput(attrs={'type': 'color', 'value': '#333333'}),
        initial=_pick_random_color,  # Set your default color hex code here
    )

    def clean(self) -> dict:
        """Check that the task has a period-wise matching Contract and does not leave orphan TimeEntries."""
        ret = super().clean()

        resource: Resource
        if (task_period := self.cleaned_data.get('period')) and (resource := self.cleaned_data.get('resource')):
            task_period = KTDateRange(task_period)
            if self.instance and self.instance.pk:
                self._check_orphan_task_entries(task_period)
            if not resource.has_contract_cover(*task_period.as_dates()):
                raise ValidationError(
                    {'period': _('Contract matching task period not found')},
                    code='contract-not-found',
                )
        return ret

    def _check_orphan_task_entries(self, task_period_range: KTDateRange) -> None:
        """Verify there are no orphan TimeEntries when changing the period."""
        lower, upper = task_period_range.as_dates()
        orphans = self.instance.task_entries.filter(Q(day_entry__day__lt=lower) | Q(day_entry__day__gte=upper)).count()

        if orphans:
            raise ValidationError(f'Would leave {orphans} orphan task_entries')

    def clean_color(self) -> None:
        if self.cleaned_data['color'] == '#000000':
            self.cleaned_data['color'] = None

    class Meta:
        model = Task
        fields = [
            'title',
            'basket',
            'project',
            'resource',
            'color',
            'period',
            'work_price',
            'on_call_price',
            'travel_price',
            'overtime_price',
            'project',
            'resource',
        ]
