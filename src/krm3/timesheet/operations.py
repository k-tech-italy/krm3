import typing
from datetime import date
from typing import Iterable

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from krm3.core.models import Resource
from krm3.utils.dates import KrmDay, KrmDateRange

if typing.TYPE_CHECKING:
    from krm3.core.models import Contract, DayEntry, Task, TaskEntry


class DayEntryProcessor:
    def __init__(self, resource: Resource, day: str | date | KrmDay, contract: 'Contract | None' = None) -> 'DayEntry':
        from krm3.core.models import Contract

        self.day: date = KrmDay(day).date
        self.resource: Resource = resource
        self.contract: Contract = contract or Contract.objects.by_day(resource, self.day)
        if not self.contract:
            raise ValueError(_('No contract found for {} on {}').formate(resource, self.day))

    def build_day(
        self, task_entries: 'Iterable[TaskEntry | dict] | None' = None, reset: bool = False, **kwargs
    ) -> 'DayEntry':
        """Build a day entry with its task_entries for the contract.

        task_entries is a list of either TaskEntry or dict for creating TaskEntry objects.
        You can mix the list with any combination of askEntry or dict.
        In the dict, the reference to the Task can be provided with the key "task" and can be either an instance
        of Task or its pk using "task_id".
        """
        from krm3.core.models import DayEntry, TaskEntry

        task_entries = task_entries or []

        day_entry, created = DayEntry.objects.get_or_create(
            day=self.day, contract=self.contract, defaults={'resource': self.resource}
        )
        if not reset and not created:
            raise RuntimeError(_('DayEntry already exists'))
        day_entry.reset(contract=self.contract, day=self.day)

        # Optional override of DayEntry values from values provided in kwargs
        for k, v in kwargs.items():
            if k in (f.name for f in DayEntry._meta.fields):
                setattr(day_entry, k, v)

        task_entries_list = []
        for task_entry_values in task_entries:
            if isinstance(task_entry_values, TaskEntry):
                task_entries_list.append(task_entry_values)
            else:
                # _build_task will check task is compatible
                task_entries_list.append(self._build_task(day_entry=day_entry, task=task_entry_values.pop('task', None), **task_entry_values))

        day_entry.refresh(task_entries_list)
        day_entry.save()
        TaskEntry.objects.bulk_create(task_entries_list)
        return day_entry

    def add_task_entry(self, task_entry: 'TaskEntry | None' = None, **kwargs) -> 'DayEntry':
        """Add task entry to DayEntry and refresh data."""
        from krm3.core.models import DayEntry

        day_entry = kwargs.pop('day_entry', DayEntry.objects.get(day=self.day, resource=self.resource))
        if task_entry is None:
            task = kwargs.pop('task')
            task_entry = self._build_task(day_entry=day_entry, task=task, **kwargs)
        task_entries = list(day_entry.taskentry_set.all())
        task_entries.append(task_entry)
        return self.build_day(task_entries=task_entries, reset=True)

    def del_task_entry(self, task_or_entry: 'int | TaskEntry | Task') -> 'DayEntry':
        """Delete task entry from DayEntry and refresh data."""
        from krm3.core.models import Task, TaskEntry

        if isinstance(task_or_entry, int):
            task_or_entry = TaskEntry.objects.select_related('day_entry').get(pk=task_or_entry)
        elif isinstance(task_or_entry, Task):
            task_or_entry = TaskEntry.objects.select_related('day_entry').get(task=task_or_entry)
        task_entries = task_or_entry.day_entry.taskentry_set.exclude(id=task_or_entry.id)
        return self.build_day(task_entries=task_entries, reset=True)

    def _build_task(self, day_entry: 'DayEntry', task: 'Task | int | None', **kwargs) -> 'TaskEntry':
        """Build a TaskEntry object with provided kwargs."""
        from krm3.core.models import Task, TaskEntry

        if task is None:
            task = Task.objects.get(pk=kwargs.pop('task_id'))
        if isinstance(task, int):
            task = Task.objects.get(pk=task)
        return TaskEntry(
            **(
                {
                    'day_shift_hours': 0,
                    'night_shift_hours': 0,
                    'travel_hours': 0,
                    'on_call_hours': 0,
                }
                | kwargs
                | {
                    'day_entry': day_entry,
                    'task': task,
                }
            )
        )
