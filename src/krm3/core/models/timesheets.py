from __future__ import annotations

from typing import TYPE_CHECKING, cast, override, Self, Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.dispatch import receiver

from .auth import Resource
from decimal import Decimal

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class TimeEntryState(models.TextChoices):
    """The state of a timesheet entry."""

    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class TimeEntryQuerySet(models.QuerySet['TimeEntry']):
    _TASK_ENTRY_FILTER = (
        models.Q(day_shift_hours__gt=0)
        | models.Q(travel_hours__gt=0)
        | models.Q(rest_hours__gt=0)
        | models.Q(night_shift_hours__gt=0)
        | models.Q(on_call_hours__gt=0)
    )

    _DAY_ENTRY_FILTER = models.Q(sick_hours__gt=0) | models.Q(holiday_hours__gt=0) | models.Q(leave_hours__gt=0)

    def open(self) -> Self:
        """Select the open time entries in this queryset.

        :return: the filtered queryset.
        """
        from .projects import POState

        return self.filter(state=POState.OPEN)

    def closed(self) -> Self:
        """Select the closed time entries in this queryset.

        :return: the filtered queryset.
        """
        from .projects import POState

        return self.filter(state=POState.CLOSED)

    def day_entries(self) -> Self:
        """Select all day entries in this queryset.

        :return: the filtered queryset.
        """
        return self.filter(self._DAY_ENTRY_FILTER & ~self._TASK_ENTRY_FILTER)

    def sick_days_and_holidays(self) -> Self:
        """Select all sick and holiday entries in this queryset.

        :return: the filtered queryset.
        """
        return self.day_entries().filter(leave_hours=0)

    def leaves(self) -> Self:
        """Select all leave entries in this queryset.

        :return: the filtered queryset.
        """
        return self.day_entries().filter(leave_hours__gt=0)

    def task_entries(self) -> Self:
        """Select all task entries in this queryset.

        :return: the filtered queryset.
        """
        return self.filter(self._TASK_ENTRY_FILTER & ~self._DAY_ENTRY_FILTER)

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
    day_shift_hours = models.DecimalField(max_digits=4, decimal_places=2)
    sick_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    holiday_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    leave_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    night_shift_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    on_call_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    travel_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    rest_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    state = models.TextField(choices=TimeEntryState, default=TimeEntryState.OPEN)  # pyright: ignore[reportArgumentType]
    comment = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, null=True, blank=True)

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='time_entries', null=True, blank=True)

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
    def total_task_hours(self) -> Decimal:
        """Compute the total task-related hours logged on this entry.

        :return: the computed total.
        """
        # NOTE: could use sum() on a comprehension, but `sum()` may also
        #       return Literal[0], which trips up the type checker
        return (
            Decimal(self.day_shift_hours)
            + Decimal(self.night_shift_hours)
            + Decimal(self.travel_hours)
            + Decimal(self.rest_hours)
        )

    @property
    def total_hours(self) -> Decimal:
        """Compute the grand total of all hours logged on this entry.

        This includes hours logged as absence.

        :return: the computed total.
        """
        # NOTE: see `total_task` hours, the same applies here
        return (
            self.total_task_hours + Decimal(self.leave_hours) + Decimal(self.sick_hours) + Decimal(self.holiday_hours)
        )

    @property
    def is_day_entry(self) -> bool:
        return self.task is None

    @property
    def is_sick_day(self) -> bool:
        return self.sick_hours > 0.0

    @property
    def is_holiday(self) -> bool:
        return self.holiday_hours > 0.0

    @property
    def is_leave(self) -> bool:
        return self.leave_hours > 0.0

    @property
    def has_day_entry_hours(self) -> bool:
        return self.is_sick_day or self.is_holiday or self.is_leave

    @property
    def is_task_entry(self) -> bool:
        return not self.is_day_entry

    @property
    def has_task_entry_hours(self) -> bool:
        return self.total_task_hours > 0.0 or self.on_call_hours > 0.0

    @override
    def clean(self) -> None:
        """Validate logged hours.

        Rules:
        - You cannot log more than one absence (sick, holiday, leave)
          in the same entry
        - Logging task entries (work, night shift, etc.) removes
          existing day entries for the related resource, and vice versa.
        - Comment is mandatory for sick days and leave hours.

        :raises exceptions.ValidationError: when any of the rules above
          is violated.
        """
        errors = []

        validators = (
            self._verify_task_hours_not_logged_in_day_entry,
            self._verify_day_hours_not_logged_in_task_entry,
            self._verify_task_and_day_hours_not_logged_together,
            self._verify_at_most_one_absence,
            self._verify_at_most_24_hours_total_logged_in_a_day,
            self._verify_sick_or_leave_time_entry_has_comment,
            self._verify_no_overtime_with_leave_entry,
        )

        for validator in validators:
            try:
                validator()
            except ValidationError as e:
                errors.append(e)

        if errors:
            raise ValidationError(errors)

        return super().clean()

    def _verify_task_hours_not_logged_in_day_entry(self) -> None:
        if self.is_day_entry and self.has_task_entry_hours:
            raise ValidationError(_('You cannot log task hours in a day entry'), code='task_hours_in_day_entry')

    def _verify_day_hours_not_logged_in_task_entry(self) -> None:
        if self.is_task_entry and self.has_day_entry_hours:
            raise ValidationError(_('You cannot log an absence in a task entry'), code='day_hours_in_task_entry')

    def _verify_at_most_one_absence(self) -> None:
        has_too_many_absences_logged = (
            len([cond for cond in (self.is_sick_day, self.is_holiday, self.is_leave) if cond]) > 1
        )
        if has_too_many_absences_logged:
            raise ValidationError(
                _('You cannot log more than one kind of absence in a day'),
                code='multiple_absence_kind',
            )

    # XXX: is this necessary?
    def _verify_task_and_day_hours_not_logged_together(self) -> None:
        if self.has_task_entry_hours and self.has_day_entry_hours:
            raise ValidationError(_('You cannot log task hours and absence hours together'), code='work_while_absent')

    def _verify_at_most_24_hours_total_logged_in_a_day(self) -> None:
        if self.total_hours > 24:
            raise ValidationError(
                _('Total hours on this time entry ({total_hours}) is over 24 hours').format(
                    date=self.date, total_hours=self.total_hours
                ),
                code='too_much_total_time_logged',
            )

        # we might be overwriting an existing time entry on the same
        # task (even None) - exclude it, as it should no longer count
        entries_on_same_day = TimeEntry.objects.filter(date=self.date, resource=self.resource).exclude(task=self.task)
        total_hours_on_same_day = sum(entry.total_hours for entry in entries_on_same_day) + self.total_hours

        if total_hours_on_same_day > 24:
            raise ValidationError(
                _('Total hours on all time entries on {date} ({total_hours}) is over 24 hours').format(
                    date=self.date, total_hours=total_hours_on_same_day
                ),
                code='too_much_total_time_logged',
            )

    def _verify_sick_or_leave_time_entry_has_comment(self) -> None:
        if (self.is_sick_day or self.is_leave) and not self.comment:
            raise ValidationError(
                _('Comment is mandatory when logging sick days or leave hours'),
                code='sick_or_on_leave_without_comment',
            )

    def _verify_no_overtime_with_leave_entry(self) -> None:
        # we might be overwriting an existing time entry on the same
        # task (even None) - exclude it, as it should no longer count
        # if we're updating the model directly, the current row on the
        # db should not count as well because we're replacing it
        entries_on_same_day = cast(
            'TimeEntryQuerySet',
            TimeEntry.objects.filter(date=self.date, resource=self.resource)
            .exclude(task=self.task)
            .exclude(pk=self.pk),
        )

        # this check only involves leaves
        if not self.is_leave and not entries_on_same_day.leaves().exists():
            return

        total_hours_on_same_day = sum(entry.total_hours for entry in entries_on_same_day) + self.total_hours
        if total_hours_on_same_day > self.resource.daily_work_hours_max:
            raise ValidationError(
                _(
                    'No overtime allowed when logging leave hours. Maximum allowed is {work_hours}, got {actual_hours}'
                ).format(work_hours=self.resource.daily_work_hours_max, actual_hours=total_hours_on_same_day),
                code='overtime_with_leave_hours',
            )


@receiver(models.signals.pre_save, sender=TimeEntry)
def validate_time_entry(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    instance.clean()


@receiver(models.signals.post_save, sender=TimeEntry)
def clear_sick_day_or_holiday_entry_on_same_day(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    open_entries = (
        cast('TimeEntryQuerySet', TimeEntry.objects).open().filter(date=instance.date, resource=instance.resource)
    )
    if instance.is_task_entry:
        overwritten = open_entries.sick_days_and_holidays()
    elif instance.is_day_entry:
        # just to be safe: remove any other existing day entry
        overwritten = open_entries.day_entries().exclude(pk=instance.pk)
    else:
        # we should never get there
        overwritten = TimeEntry.objects.none()
    overwritten.delete()


@receiver(models.signals.post_save, sender=TimeEntry)
def clear_task_entries_on_same_day(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    open_entries = (
        cast('TimeEntryQuerySet', TimeEntry.objects).open().filter(date=instance.date, resource=instance.resource)
    )
    if instance.is_day_entry and instance.leave_hours == 0:
        overwritten = open_entries.task_entries()
    elif instance.is_task_entry:
        # just to be safe: remove any other existing task entry for the
        # `instance`'s task
        overwritten = open_entries.filter(task=instance.task).exclude(pk=instance.pk)
    else:
        # we should never get there
        overwritten = TimeEntry.objects.none()
    overwritten.delete()
