from __future__ import annotations

from typing import Iterable

import djclick as click
from django.apps import apps
from django.db import connection, models
from django.db.models import Min

from krm3.core.contracts import ContractSolver
from krm3.core.models import Contract
from krm3.utils.dates import KrmDateRange


def _inject_task_entry_fields() -> tuple[models.Model, models.Model]:
    """Re-add removed fields to TaskEntry so the migration can read them."""
    TaskEntry = apps.get_model('core', 'TaskEntry')
    Resource = apps.get_model('core', 'Resource')
    TimesheetSubmission = apps.get_model('core', 'TimesheetSubmission')
    SpecialLeaveReason = apps.get_model('core', 'SpecialLeaveReason')
    fields = [
        models.DateTimeField(auto_now=True, name='last_modified'),
        models.DateField(name='date'),
        models.DecimalField(max_digits=4, decimal_places=2, default=0.0, name='holiday_hours'),
        models.DecimalField(max_digits=4, decimal_places=2, default=0.0, name='leave_hours'),
        models.DecimalField(max_digits=4, decimal_places=2, default=0.0, name='rest_hours'),
        models.DecimalField(max_digits=4, decimal_places=2, default=0.0, name='sick_hours'),
        models.DecimalField(max_digits=4, decimal_places=2, default=0.0, name='special_leave_hours'),
        models.ForeignKey(Resource, on_delete=models.deletion.PROTECT, name='resource'),
        models.ForeignKey(
            TimesheetSubmission, blank=True, null=True, on_delete=models.deletion.SET_NULL, name='timesheet'
        ),
        models.ForeignKey(
            SpecialLeaveReason,
            blank=True,
            null=True,
            on_delete=models.deletion.PROTECT,
            name='special_leave_reason',
        ),
        models.DecimalField(max_digits=4, decimal_places=2, default=0.0, name='bank_from'),
        models.DecimalField(max_digits=4, decimal_places=2, default=0.0, name='bank_to'),
        models.CharField(blank=True, null=True, name='protocol_number'),
    ]
    for field in fields:
        field.contribute_to_class(TaskEntry, field.name)

    return TaskEntry, TimesheetSubmission


@click.command()
def command() -> None:
    """Manual data migrations for 0033."""
    migrate_dates()
    migrate_time_entries()


def migrate_dates() -> None:
    """Replace start_date, end_date with period."""
    with connection.cursor() as cursor:
        for model in ['project', 'po', 'task']:
            cursor.execute(f"UPDATE core_{model} SET period = daterange(start_date, end_date, '[]');")


def ensure_contracts(TaskEntry):
    for rec in TaskEntry.objects.values('resource_id').annotate(min_date=Min('date')):
        if Contract.objects.filter(resource_id=rec['resource_id']).first() is None:
            Contract.objects.create(resource_id=rec['resource_id'], period=(rec['min_date'], None))


def migrate_time_entries():
    """Migrate TaskEntry to DayEntry for migration core 0033."""
    TaskEntry, TimesheetSubmission = _inject_task_entry_fields()
    DayEntry = apps.get_model('core', 'DayEntry')

    timesheets = {}
    for ts in TimesheetSubmission.objects.all():
        for d in KrmDateRange(ts.period):
            timesheets[(d.date, ts.resource_id)] = ts

    # Silencing the cleans
    DayEntry._verify_timesheet_not_submitted = lambda x: ...
    DayEntry._verify_bank_hours_balance_limits = lambda x: ...
    TaskEntry.clean = lambda *args, **kwargs: ...

    day_entries = {
        k: {'task_entries': []}
        for k in list(TaskEntry.objects.distinct('resource_id', 'date').values_list('resource_id', 'date'))
    }

    resource_ids = {r[0] for r in day_entries.keys()}
    ensure_contracts(TaskEntry)
    contract_solver = ContractSolver(resource_ids=resource_ids)

    de_count = 0
    te_count = 0
    for te in list(TaskEntry.objects.select_related('timesheet').all()):
        key = te.resource_id, te.date
        contract = contract_solver.solve(te.resource, te.date)

        day_entries[key]['day'] = te.date
        day_entries[key]['resource_id'] = te.resource_id
        day_entries[key]['closed'] = (te.timesheet and te.timesheet.closed) or False
        day_entries[key]['contract_id'] = contract.id
        day_entries[key]['is_holiday'] = contract.is_holiday(te.date)
        day_entries[key]['due_hours'] = contract.get_due_hours(te.date)
        day_entries[key]['timesheet'] = timesheets.get(key)

        if te.task_id is None:  # it's a day_entry
            de_count += 1
            day_entries[key]['asked_holiday'] = not day_entries[key]['is_holiday'] and bool(te.holiday_hours)
            day_entries[key]['leave_hours'] = te.leave_hours
            day_entries[key]['rest_hours'] = te.rest_hours
            day_entries[key]['special_leave_hours'] = te.special_leave_hours
            day_entries[key]['special_leave_reason'] = te.special_leave_reason
            day_entries[key]['bank'] = te.bank_to - te.bank_from
            day_entries[key]['is_sick'] = bool(te.sick_hours)
            day_entries[key]['protocol_number'] = te.protocol_number
        else:  # it's a task_entry
            te_count += 1
            day_entries[key]['task_entries'].append(te)

    TaskEntry.objects.filter(day_entry_id__isnull=True).delete()

    for de in day_entries.values():
        de_count += 1
        task_entries = de.pop('task_entries')
        de = DayEntry(**de)
        de.refresh(task_entries=task_entries, drop_existing=False)
        de.save()
        for te in task_entries:
            te_count += 1
            te.day_entry = de
            te.save()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE core_dayentry p
            SET last_modified = (SELECT MAX(last_modified)
                                 FROM core_taskentry c
                                 WHERE c.day_entry_id = p.id)
            WHERE EXISTS(SELECT 1
                         FROM core_taskentry c
                         WHERE c.day_entry_id = p.id)
            """
        )
