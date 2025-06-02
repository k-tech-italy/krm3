from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Iterable, Self, cast, override

from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django_pydantic_field import SchemaField

from .auth import Resource
from ..pyd_models import Hours

if TYPE_CHECKING:
    import datetime

    from django.contrib.auth.models import AbstractUser
    from django.db.models.base import ModelBase


class SpecialLeaveReasonQuerySet(models.QuerySet):
    def valid_between(self, start_date: datetime.date | None, end_date: datetime.date | None) -> Self:
        match start_date, end_date:
            case None, None:
                return self
            case start, end if start is not None and end is not None:
                return self.filter(
                    models.Q(from_date__isnull=True, to_date__isnull=True)
                    | models.Q(from_date__isnull=True, to_date__gte=end)
                    | models.Q(from_date__lte=start, to_date__isnull=True)
                    | models.Q(from_date__lte=start, to_date__gte=end)
                )
            case _:
                raise ValueError('Start and end must both be either dates or None')


class SpecialLeaveReason(models.Model):
    """A reason for special leave."""

    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    from_date = models.DateField(blank=True, null=True)
    to_date = models.DateField(blank=True, null=True)

    objects = SpecialLeaveReasonQuerySet.as_manager()

    def __str__(self) -> str:
        if self.from_date and self.to_date:
            interval = f' ({self.from_date} - {self.to_date})'
        elif self.from_date:
            interval = f' ({self.from_date} - ...)'
        elif self.to_date:
            interval = f' (... - {self.to_date})'
        else:
            interval = ''
        return f'{self.title}{interval}'

    @override
    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.full_clean()
        return super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
        )

    @override
    def clean(self) -> None:
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValidationError(_('"from_date" must not be later than "to_date"'), code='invalid_date_interval')
        return super().clean()

    def is_not_valid_yet(self, date: datetime.date) -> bool:
        return self.from_date is not None and date < self.from_date

    def is_expired(self, date: datetime.date) -> bool:
        return self.to_date is not None and date > self.to_date

    def is_valid(self, date: datetime.date) -> bool:
        return not self.is_not_valid_yet(date) and not self.is_expired(date)


class TimeEntryState(models.TextChoices):
    """The state of a timesheet entry."""

    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class TimeEntryQuerySet(models.QuerySet['TimeEntry']):
    _TASK_ENTRY_FILTER = (
        models.Q(day_shift_hours__gt=0)
        | models.Q(travel_hours__gt=0)
        | models.Q(night_shift_hours__gt=0)
        | models.Q(on_call_hours__gt=0)
    )

    _DAY_ENTRY_FILTER = (
        models.Q(sick_hours__gt=0)
        | models.Q(holiday_hours__gt=0)
        | models.Q(rest_hours__gt=0)
        | models.Q(leave_hours__gt=0)
        | models.Q(special_leave_hours__gt=0)
    )

    _REGULAR_LEAVE_ENTRY_FILTER = models.Q(leave_hours__gt=0, special_leave_hours=0, special_leave_reason__isnull=True)
    _SPECIAL_LEAVE_ENTRY_FILTER = models.Q(leave_hours=0, special_leave_hours__gt=0, special_leave_reason__isnull=False)

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
        return self.day_entries().filter(self._REGULAR_LEAVE_ENTRY_FILTER)

    def special_leaves(self) -> Self:
        """Select all leave entries in this queryset.

        :return: the filtered queryset.
        """
        return self.day_entries().filter(self._SPECIAL_LEAVE_ENTRY_FILTER)

    def task_entries(self) -> Self:
        """Select all task entries in this queryset.

        :return: the filtered queryset.
        """
        return self.filter(self._TASK_ENTRY_FILTER & ~self._DAY_ENTRY_FILTER)

    def entries_preventing_overtime_on_same_day(self) -> Self:
        """Select all entries restricting the limit of hours logged per day.

        :return: the filtered queryset.
        """
        return self.filter(
            self._REGULAR_LEAVE_ENTRY_FILTER | self._SPECIAL_LEAVE_ENTRY_FILTER | models.Q(rest_hours__gt=0)
        )

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
    state = models.TextField(choices=TimeEntryState, default=TimeEntryState.OPEN)  # pyright: ignore[reportArgumentType]
    comment = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, null=True, blank=True)

    hours: Hours = SchemaField()
    special_leave_reason = models.ForeignKey(SpecialLeaveReason, on_delete=models.PROTECT, null=True, blank=True)

    day_shift_hours = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    sick_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    holiday_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    leave_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    special_leave_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    night_shift_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    on_call_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    travel_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    rest_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)

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

    @override
    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.full_clean()
        return super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
        )

    @property
    def total_task_hours(self) -> Decimal:
        """Compute the total task-related hours logged on this entry.

        :return: the computed total.
        """
        # NOTE: could use sum() on a comprehension, but `sum()` may also
        #       return Literal[0], which trips up the type checker
        return Decimal(self.hours.day_shift) + Decimal(self.hours.night_shift) + Decimal(self.hours.travel)

    @property
    def total_hours(self) -> Decimal:
        """Compute the grand total of all hours logged on this entry.

        This includes hours logged as absence.

        :return: the computed total.
        """
        # NOTE: see `total_task` hours, the same applies here
        return (
            self.total_task_hours
            + Decimal(self.hours.leave)
            + Decimal(self.hours.special_leave)
            + Decimal(self.hours.sick)
            + Decimal(self.hours.holiday)
            + Decimal(self.hours.rest)
        )

    @property
    def is_day_entry(self) -> bool:
        return self.task is None

    @property
    def is_sick_day(self) -> bool:
        return self.hours.sick > 0.0

    @property
    def is_holiday(self) -> bool:
        return self.hours.holiday > 0.0

    @property
    def is_leave(self) -> bool:
        return self.hours.leave > 0.0

    @property
    def is_rest(self) -> bool:
        return self.hours.rest > 0.0

    @property
    def is_special_leave(self) -> bool:
        return self.hours.special_leave > 0.0 and self.hours.special_leave_reason_id

    @property
    def has_day_entry_hours(self) -> bool:
        return self.is_sick_day or self.is_holiday or self.is_leave or self.is_special_leave or self.is_rest

    @property
    def is_task_entry(self) -> bool:
        return not self.is_day_entry

    @property
    def has_task_entry_hours(self) -> bool:
        return self.total_task_hours > 0.0 or self.hours.on_call > 0.0

    @property
    def prevents_overtime_on_same_day(self) -> bool:
        return self.is_leave or self.is_special_leave or self.is_rest

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
        super().clean()

        errors = []
        validators = (
            self._verify_task_hours_not_logged_in_day_entry,
            self._verify_day_hours_not_logged_in_task_entry,
            self._verify_task_and_day_hours_not_logged_together,
            self._verify_at_most_one_absence,
            self._verify_at_most_24_hours_total_logged_in_a_day,
            self._verify_sick_time_entry_has_comment,
            self._verify_leave_is_either_regular_or_special,
            self._verify_reason_only_on_special_leave,
            self._verify_special_leave_reason_is_valid,
            self._verify_no_overtime_with_leave_or_rest_entry,
        )

        for validator in validators:
            try:
                validator()
            except ValidationError as e:
                errors.append(e)

        if errors:
            raise ValidationError(errors)

    def _verify_task_hours_not_logged_in_day_entry(self) -> None:
        if self.is_day_entry and self.has_task_entry_hours:
            raise ValidationError(_('You cannot log task hours in a day entry'), code='task_hours_in_day_entry')

    def _verify_day_hours_not_logged_in_task_entry(self) -> None:
        if self.is_task_entry and self.has_day_entry_hours:
            raise ValidationError(_('You cannot log non-task hours in a task entry'), code='day_hours_in_task_entry')

    def _verify_at_most_one_absence(self) -> None:
        has_too_many_day_entry_hours_logged = (
            len([cond for cond in (self.is_sick_day, self.is_holiday, self.is_leave, self.is_special_leave) if cond])
            > 1
        )
        if has_too_many_day_entry_hours_logged:
            raise ValidationError(
                _('You cannot log more than one kind of non-task hours in a day'),
                code='multiple_absence_kind',
            )

    # XXX: is this necessary?
    def _verify_task_and_day_hours_not_logged_together(self) -> None:
        if self.has_task_entry_hours and self.has_day_entry_hours:
            raise ValidationError(_('You cannot log task hours and non-task hours together'), code='work_while_absent')

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

    def _verify_sick_time_entry_has_comment(self) -> None:
        if self.is_sick_day and not self.comment:
            raise ValidationError(
                _('Comment is mandatory when logging sick days or leave hours'),
                code='sick_without_comment',
            )

    def _verify_leave_is_either_regular_or_special(self) -> None:
        if self.leave_hours and self.special_leave_hours:
            raise ValidationError(
                _('Cannot log hours on both regular and special leave'), code='regular_and_special_leave'
            )

    def _verify_reason_only_on_special_leave(self) -> None:
        if self.special_leave_reason and not self.special_leave_hours:
            raise ValidationError(_('Only a special leave can have a reason'), code='reason_on_non_special_leave')
        if not self.special_leave_reason and self.special_leave_hours:
            raise ValidationError(
                _('Reason is required when logging a special leave'), code='no_reason_on_special_leave'
            )

    def _verify_special_leave_reason_is_valid(self) -> None:
        if not self.is_special_leave:
            return
        if not self.special_leave_reason.is_valid(self.date):
            raise ValidationError(
                _('Reason "{title}" is not valid on {date}').format(
                    title=self.special_leave_reason.title, date=self.date
                ),
                code='invalid_special_leave_reason',
            )

    def _verify_no_overtime_with_leave_or_rest_entry(self) -> None:
        # we might be overwriting an existing time entry on the same
        # task (even None) - exclude it, as it should no longer count
        # if we're updating the model directly, the current row on the
        # db should not count as well because we're replacing it
        all_entries = cast('TimeEntryQuerySet', TimeEntry.objects.filter(date=self.date, resource=self.resource))

        other_entries_on_same_day = all_entries.exclude(task=self.task).exclude(pk=self.pk)

        # this check only involves leave (both kinds) and rest entries
        if (
            not self.prevents_overtime_on_same_day
            and not other_entries_on_same_day.entries_preventing_overtime_on_same_day().exists()
        ):
            return

        total_hours_on_same_day = sum(entry.total_hours for entry in other_entries_on_same_day) + self.total_hours
        if total_hours_on_same_day > self.resource.daily_work_hours_max:
            raise ValidationError(
                _(
                    'No overtime allowed when logging a {kind}. Maximum allowed is {work_hours}, got {actual_hours}'
                ).format(
                    kind='rest' if self.is_rest else 'leave',
                    work_hours=self.resource.daily_work_hours_max,
                    actual_hours=total_hours_on_same_day,
                ),
                code='overtime_while_resting_or_on_leave',
            )


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
    if instance.is_sick_day or instance.is_holiday:
        overwritten = open_entries.task_entries()
    elif instance.is_task_entry:
        # just to be safe: remove any other existing task entry for the
        # `instance`'s task
        overwritten = open_entries.filter(task=instance.task).exclude(pk=instance.pk)
    else:
        overwritten = TimeEntry.objects.none()
    overwritten.delete()
