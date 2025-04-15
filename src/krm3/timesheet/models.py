from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Self, override


from django.core import exceptions
from django.db import models
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from krm3.core import models as core_models

if TYPE_CHECKING:
    from decimal import Decimal
    from django.db.models.fields.related_descriptors import RelatedManager

    from krm3.accounting.models import InvoiceEntry
    from django.contrib.auth.models import AbstractUser

_DEFAULT_START_DATE = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)


class POState(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class PO(models.Model):
    """A PO for a project."""

    ref = models.CharField(max_length=50)
    is_billable = models.BooleanField(default=True)
    state = models.TextField(choices=POState, default=POState.OPEN)  # type: ignore
    start_date = models.DateField(default=_DEFAULT_START_DATE)
    end_date = models.DateField(null=True, blank=True)

    project = models.ForeignKey(core_models.Project, on_delete=models.CASCADE)

    class Meta:
        constraints = (models.UniqueConstraint(fields=('ref', 'project'), name='unique_ref_project_in_po'),)
        verbose_name = 'PO'
        verbose_name_plural = 'POs'

    @override
    def __str__(self) -> str:
        return self.ref


class Basket(models.Model):
    """Defines the cumulative availability of person-hours for a PO."""

    title = models.CharField(max_length=200)
    initial_capacity = models.DecimalField(max_digits=10, decimal_places=2)
    # XXX: should we SET_NULL? or rather SET(next in line if any)?
    follows = models.OneToOneField('self', on_delete=models.RESTRICT, null=True, blank=True, related_name='followed_by')

    po = models.ForeignKey(PO, on_delete=models.CASCADE)

    if TYPE_CHECKING:
        invoice_entries: RelatedManager[InvoiceEntry]

    @override
    def __str__(self) -> str:
        return self.title

    def tasks(self) -> models.QuerySet[Task]:
        """Return the tasks attached to this basket.

        :return: a queryset of related `Task`s.
        """
        return Task.objects.filter(basket_title=self.title)

    def current_capacity(self) -> Decimal:
        """Compute the basket's current capacity based on invoiced hours.

        :return: the computed capacity
        """
        invoiced_hours = self.invoice_entries.values_list('amount', flat=True)
        return self.initial_capacity - sum(invoiced_hours)

    def current_projected_capacity(self) -> Decimal:
        """Compute the basket' current capacity.

        Calculations use both invoices and open time entries.

        :return: the computed capacity
        """
        time_entries = TimeEntry.objects.open().filter(task__in=self.tasks())  # pyright: ignore
        logged_hours = sum(entry.total_work_hours for entry in time_entries)
        return self.current_capacity() - logged_hours


class TaskQuerySet(models.QuerySet[type['Task']]):
    def active_between(self, start: datetime.date, end: datetime.date) -> Self:
        return self.filter(start_date__lte=end, end_date__gte=start)

    def assigned_to(self, resource: core_models.Resource | int) -> Self:
        return self.filter(resource=resource)

    def filter_acl(self, user: type[AbstractUser]) -> Self:
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
            {'core.manage_any_project', 'core.view_any_project'}
        ):
            return self.all()
        return self.filter(resource__user=user)


class Task(models.Model):
    """A task assigned to a resource."""

    title = models.CharField(max_length=200)
    basket_title = models.CharField(max_length=200, null=True, blank=True)
    # TODO: validate this
    color = models.TextField(null=True, blank=True)
    start_date = models.DateField(default=_DEFAULT_START_DATE)
    end_date = models.DateField(null=True, blank=True)
    # TODO: make prices currency-aware
    work_price = models.DecimalField(max_digits=10, decimal_places=2)
    on_call_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    travel_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    overtime_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    project = models.ForeignKey(core_models.Project, on_delete=models.CASCADE)
    # XXX: should we retain this instead?
    resource = models.ForeignKey(core_models.Resource, on_delete=models.CASCADE)

    objects = TaskQuerySet.as_manager()

    if TYPE_CHECKING:
        time_entries: RelatedManager[TimeEntry]

    @override
    def __str__(self) -> str:
        return self.title

    def time_entries_between(self, start: datetime.date, end: datetime.date) -> models.QuerySet[TimeEntry]:
        return self.time_entries.filter(date__range=(start, end))


class TimeEntryState(models.TextChoices):
    """The state of a timesheet entry."""

    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class TimeEntryQuerySet(models.QuerySet['TimeEntry']):
    def open(self) -> Self:
        """Select the open time entries in this queryset.

        :return: the filtered queryset.
        """
        return self.filter(state=POState.OPEN)

    def filter_acl(self, user: type[AbstractUser]) -> Self:
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
            {'timesheet.manage_any_timesheet', 'timesheet.view_any_timesheet'}
        ):
            return self.all()
        return self.filter(resource__user=user)


class TimeEntry(models.Model):
    """A timesheet entry."""

    date = models.DateField()
    last_modified = models.DateTimeField(auto_now=True)
    work_hours = models.DecimalField(max_digits=4, decimal_places=2)
    sick_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    holiday_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    leave_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    on_call_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    travel_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    rest_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    state = models.TextField(choices=TimeEntryState, default=TimeEntryState.OPEN)  # type: ignore
    comment = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, null=True, blank=True)

    resource = models.ForeignKey(core_models.Resource, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_entries')

    objects = TimeEntryQuerySet.as_manager()

    class Meta:
        verbose_name_plural = 'Time entries'
        permissions = [
            ('view_any_timesheet', "Can view(only) everybody's timesheets"),
            ('manage_any_timesheet', "Can view, and manage everybody's timesheets"),
        ]

    @override
    def __str__(self) -> str:
        return f'{self.date}: {self.resource} on "{self.task}" ({self.state})'

    @property
    def total_work_hours(self) -> Decimal:
        """Compute the total task-related hours logged on this entry.

        :return: the computed total.
        """
        return self.work_hours + self.leave_hours + self.overtime_hours + self.travel_hours + self.rest_hours

    @override
    def clean(self) -> None:
        """Validate logged hours.

        Rules:
        - You cannot log more than one full-day absence (sick, holiday)
          in the same entry
        - You cannot log task-related hours (work, overtime, etc.)
          if the entry already has a full-day absence logged.

        :raises exceptions.ValidationError: when any of the rules above
          is violated.
        """
        errors = []

        is_work_day = any(
            hours > 0.0
            for hours in (
                self.work_hours,
                self.leave_hours,
                self.overtime_hours,
                self.on_call_hours,
                self.rest_hours,
                self.travel_hours,
            )
        )
        is_sick_day = self.sick_hours > 0.0
        is_holiday = self.holiday_hours > 0.0

        if is_sick_day and is_holiday:
            errors.append(
                exceptions.ValidationError(
                    _('You cannot log more than one type of full-day absences in a day.'),
                    code='multiple_full_day_absence_hours',
                )
            )

        is_full_day_absence = is_sick_day or is_holiday
        if is_work_day and is_full_day_absence:
            errors.append(
                exceptions.ValidationError(
                    _('You cannot log work-related hours on %(absence)s.'),
                    params={'absence': _('a sick day') if is_sick_day else _('a holiday')},
                    code='work_during_full_day_absence',
                )
            )

        if errors:
            raise exceptions.ValidationError(errors)


@receiver(models.signals.pre_save, sender=TimeEntry)
def validate_time_entry(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    instance.clean()
