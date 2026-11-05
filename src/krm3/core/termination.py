"""Termination of an open-ended contract: what it removes or amends, and how it is applied."""

from __future__ import annotations

import dataclasses
import datetime
import typing

from django.db import models, transaction
from ktcalendars import KTDateRange
from psycopg.types.range import DateRange

from krm3.core.models import Contract, DayEntry, Task, TimesheetSubmission

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet


class ContractModifiedError(Exception):
    """The contract changed after its termination was started."""


@dataclasses.dataclass(frozen=True)
class TerminationOutcome:
    day_entries: int
    deleted_tasks: int
    truncated_tasks: int
    deleted_submissions: int
    truncated_submissions: int


@dataclasses.dataclass(frozen=True)
class ContractTermination:
    """Ending `contract` on `termination_date`, the last day of the contract (included).

    For the contract's resource, termination:

    - deletes the day entries after the termination date, closed ones included (with their task entries);
    - deletes the tasks starting after the termination date;
    - truncates at the termination date the tasks that start on or before it and end after it (or never);
    - deletes the timesheet submissions starting after the termination date;
    - truncates at the termination date the submissions that span it, rebuilding the snapshot of the closed ones.

    The termination is applied only if the contract still has the version read when it was started
    (see `apply`).
    """

    contract: Contract
    termination_date: datetime.date

    @property
    def end(self) -> datetime.date:
        """The exclusive upper bound of the truncated periods: the day after the termination date."""
        return self.termination_date + datetime.timedelta(days=1)

    @property
    def _after(self) -> DateRange:
        return DateRange(self.end, None, '[)')

    def day_entries(self) -> QuerySet[DayEntry]:
        return DayEntry.objects.filter(resource_id=self.contract.resource_id, day__gt=self.termination_date).order_by(
            'day'
        )

    def deleted_tasks(self) -> QuerySet[Task]:
        return (
            Task.objects.filter(resource_id=self.contract.resource_id, period__startswith__gt=self.termination_date)
            .select_related('project')
            .order_by('period', 'pk')
        )

    def truncated_tasks(self) -> QuerySet[Task]:
        return (
            Task.objects.filter(
                resource_id=self.contract.resource_id,
                period__startswith__lte=self.termination_date,
                period__overlap=self._after,
            )
            .select_related('project')
            .order_by('period', 'pk')
        )

    def deleted_submissions(self) -> QuerySet[TimesheetSubmission]:
        return TimesheetSubmission.objects.filter(
            resource_id=self.contract.resource_id, period__startswith__gt=self.termination_date
        ).order_by('period')

    def truncated_submissions(self) -> QuerySet[TimesheetSubmission]:
        return TimesheetSubmission.objects.filter(
            resource_id=self.contract.resource_id,
            period__startswith__lte=self.termination_date,
            period__overlap=self._after,
        ).order_by('period')

    @transaction.atomic
    def apply(self, version: int) -> TerminationOutcome:
        """Terminate the contract and remove or truncate what lies after the termination date.

        :param version: the contract version read when the termination was started. The contract row is locked
            (SELECT ... FOR UPDATE) only if it still has this version, before any other change.
        :raise ContractModifiedError: if the contract has been changed or deleted since that version was read.
        """
        contract = Contract.objects.select_for_update().filter(pk=self.contract.pk, version=version).first()
        if contract is None:
            raise ContractModifiedError(self.contract.pk)

        truncated_submissions = list(self.truncated_submissions())
        truncated_tasks = list(self.truncated_tasks())

        # The model querysets refuse to delete closed entries and submissions followed by closed ones: termination
        # deliberately amends closed timesheets, so the plain QuerySet.delete is used.
        deleted_submissions = models.QuerySet.delete(self.deleted_submissions())[1].get(
            TimesheetSubmission._meta.label, 0
        )
        day_entries = models.QuerySet.delete(self.day_entries())[1].get(DayEntry._meta.label, 0)

        contract.period = KTDateRange.from_start_end(contract.period.lower, self.termination_date)
        contract.save()

        deleted_tasks = self.deleted_tasks().delete()[1].get(Task._meta.label, 0)
        for task in truncated_tasks:
            task.period = DateRange(task.period.lower, self.end, '[)')
            task.save()

        # after the deletions above, so that the rebuilt snapshots no longer include the removed days
        for submission in truncated_submissions:
            submission.period = DateRange(submission.period.lower, self.end, '[)')
            submission.save()

        return TerminationOutcome(
            day_entries=day_entries,
            deleted_tasks=deleted_tasks,
            truncated_tasks=len(truncated_tasks),
            deleted_submissions=deleted_submissions,
            truncated_submissions=len(truncated_submissions),
        )
