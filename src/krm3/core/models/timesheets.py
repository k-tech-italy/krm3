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
                ValidationError(
                    _('You cannot log more than one type of full-day absences in a day.'),
                    code='multiple_full_day_absence_hours',
                )
            )

        is_full_day_absence = is_sick_day or is_holiday
        if is_work_day and is_full_day_absence:
            errors.append(
                ValidationError(
                    _('You cannot log work-related hours on %(absence)s.'),
                    params={'absence': _('a sick day') if is_sick_day else _('a holiday')},
                    code='work_during_full_day_absence',
                )
            )

        if errors:
            raise ValidationError(errors)


@receiver(models.signals.pre_save, sender=TimeEntry)
def validate_time_entry(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    instance.clean()
