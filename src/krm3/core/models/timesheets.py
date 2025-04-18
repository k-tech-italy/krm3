from __future__ import annotations

from typing import TYPE_CHECKING, override, Self, Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.dispatch import receiver

from .auth import Resource

if TYPE_CHECKING:
    from decimal import Decimal
    from django.contrib.auth.models import AbstractUser


class TimeEntryState(models.TextChoices):
    """The state of a timesheet entry."""

    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class TimeEntryQuerySet(models.QuerySet['TimeEntry']):
    def open(self) -> Self:
        """Select the open time entries in this queryset.

        :return: the filtered queryset.
        """
        from .projects import POState

        return self.filter(state=POState.OPEN)

    def filter_acl(self, user: AbstractUser) -> Self:
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
            {'core.manage_any_timesheet', 'core.view_any_timesheet'}
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

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='time_entries')

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
        return self.work_hours + self.overtime_hours + self.travel_hours + self.rest_hours

    @property
    def total_hours(self) -> Decimal:
        """Compute the grand total of all hours logged on this entry.

        This includes hours logged as absence.

        :return: the computed total.
        """
        return self.total_work_hours + self.leave_hours + self.sick_hours + self.holiday_hours

    @override
    def clean(self) -> None:
        """Validate logged hours.

        Rules:
        - You cannot log more than one absence (sick, holiday, leave)
          in the same entry
        - You cannot log task-related hours (work, overtime, etc.)
          if the entry already has an absence logged.

        :raises exceptions.ValidationError: when any of the rules above
          is violated.
        """
        errors = []

        has_task_hours_logged = any(
            hours > 0.0
            for hours in (
                self.work_hours,
                self.overtime_hours,
                self.on_call_hours,
                self.rest_hours,
                self.travel_hours,
            )
        )
        is_sick_day = self.sick_hours > 0.0
        is_holiday = self.holiday_hours > 0.0
        is_leave = self.leave_hours > 0.0

        has_too_many_absences_logged = len([cond for cond in (is_sick_day, is_holiday, is_leave) if cond]) > 1
        if has_too_many_absences_logged:
            errors.append(
                ValidationError(
                    _('You cannot log more than one kind of absence in a day.'),
                    code='multiple_absence_kind',
                )
            )

        is_day_entry = is_sick_day or is_holiday or is_leave
        if has_task_hours_logged and is_day_entry:
            errors.append(
                ValidationError(_('You cannot log task hours and absence hours together.'), code='work_while_absent')
            )

        if errors:
            raise ValidationError(errors)


@receiver(models.signals.pre_save, sender=TimeEntry)
def validate_time_entry(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    instance.clean()
