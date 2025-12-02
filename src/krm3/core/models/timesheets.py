from __future__ import annotations

import datetime
from decimal import Decimal
from textwrap import shorten
from typing import TYPE_CHECKING, Any, Iterable, Self, cast, override

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import ArrayField, DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet
from constance import config

from .auth import Resource
from krm3.utils.dates import KrmDay

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from django.db.models.base import ModelBase


DAYTIME_WORK_HOURS_MAX = 16
NIGHTTIME_WORK_HOURS_MAX = 8


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


class TimesheetSubmissionManager(models.Manager):
    """Custom Manager for TimesheetSubmission with utility methods."""

    def get_closed_in_period(
        self, from_date: datetime.date, to_date: datetime.date, resources: Resource | Iterable[Resource]
    ) -> QuerySet[TimesheetSubmission]:
        """
        Return all `TimesheetSubmission`s closed within the given date range for the given `resources`.

        `resources` may also be a singular `Resource`.
        """
        if isinstance(resources, Resource):
            resources = [resources]
        return self.filter(
            period__overlap=(from_date, to_date + datetime.timedelta(days=1)), closed=True, resource__in=resources
        )


class TimesheetSubmission(models.Model):
    """A submitted timesheet."""

    period = DateRangeField(help_text=_('N.B.: End date is the day after the actual end date'))
    closed = models.BooleanField(default=True)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    timesheet = models.JSONField(null=True, blank=True, default=dict)

    objects: TimesheetSubmissionManager = TimesheetSubmissionManager()

    class Meta:
        constraints = [
            ExclusionConstraint(
                name='exclude_overlapping_timesheets',
                expressions=[
                    ('period', RangeOperators.OVERLAPS),
                    ('resource', RangeOperators.EQUAL),
                ],
            )
        ]

    def __str__(self) -> str:
        if self.period.lower.day == self.period.upper.day == 1:
            return self.period.lower.strftime('%Y %b')
        end_dt = self.period.upper - datetime.timedelta(days=1)
        return f'{self.period.lower.strftime("%Y-%m-%d")} - {end_dt.strftime("%Y-%m-%d")}'

    @override
    def save(self, *, force_insert: bool = False, force_update: bool = False, using=None, update_fields=None) -> None:  # noqa: D102, ANN001
        # We do not check for constraints as we want to surface the detailed errors from the DB when saving
        self.full_clean(validate_unique=False, validate_constraints=False)
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    @override
    def clean(self) -> None:
        super().clean()
        self.timesheet = self.calculate_timesheet() if self.closed else None

    def calculate_timesheet(self) -> dict:
        """Retrieve the resource timesheet data (DTO dict) for a specific date interval."""
        from krm3.timesheet.api.serializers import TimesheetSerializer  # noqa: PLC0415
        from krm3.timesheet.dto import TimesheetDTO  # noqa: PLC0415

        lower = KrmDay(self.period.lower).date
        upper = KrmDay(self.period.upper).date
        timesheet = TimesheetDTO().fetch(self.resource, lower, upper + relativedelta(days=1))
        return TimesheetSerializer(timesheet).data


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
        | models.Q(bank_to__gt=0)
        | models.Q(bank_from__gt=0)
    )

    _REGULAR_LEAVE_ENTRY_FILTER = models.Q(leave_hours__gt=0)
    _SPECIAL_LEAVE_ENTRY_FILTER = models.Q(special_leave_hours__gt=0, special_leave_reason__isnull=False)

    def open(self) -> Self:
        """Select the open time entries in this queryset.

        :return: the filtered queryset.
        """
        return self.filter(Q(timesheet__isnull=True) | Q(timesheet__closed=False))

    def closed(self) -> Self:
        """Select the closed time entries in this queryset.

        :return: the filtered queryset.
        """
        return self.filter(timesheet__isnull=False, timesheet__closed=True)

    def day_entries(self) -> Self:
        """Select all day entries in this queryset.

        :return: the filtered queryset.
        """
        return self.filter(self._DAY_ENTRY_FILTER & ~self._TASK_ENTRY_FILTER)

    def sick_days_and_holidays(self) -> Self:
        """Select all sick and holiday entries in this queryset.

        :return: the filtered queryset.
        """
        return self.day_entries().filter(leave_hours=0, special_leave_hours=0)

    def leaves(self) -> Self:
        """Select all leave entries in this queryset.

        :return: the filtered queryset.
        """
        return self.day_entries().filter(self._REGULAR_LEAVE_ENTRY_FILTER)

    def special_leaves(self) -> Self:
        """Select all special leave entries in this queryset.

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
    day_shift_hours = models.DecimalField(max_digits=4, decimal_places=2)
    sick_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    holiday_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    leave_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    special_leave_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    special_leave_reason = models.ForeignKey(SpecialLeaveReason, on_delete=models.PROTECT, null=True, blank=True)
    night_shift_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    on_call_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    travel_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    rest_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    bank_from = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    bank_to = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    comment = models.TextField(null=True, blank=True)
    protocol_number = models.CharField(null=True, blank=True)
    metadata = models.JSONField(default=dict, null=True, blank=True)
    timesheet = models.ForeignKey(TimesheetSubmission, on_delete=models.SET_NULL, null=True, blank=True)

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='time_entries', null=True, blank=True)

    objects = TimeEntryQuerySet.as_manager()

    class Meta:
        verbose_name_plural = 'Time entries'
        permissions = [
            ('view_any_timesheet', "Can view(only) everybody's timesheets"),
            ('manage_any_timesheet', "Can view, and manage everybody's timesheets"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(day_shift_hours__range=(0, DAYTIME_WORK_HOURS_MAX)), name='day_shift_hours_range'
            ),
            models.CheckConstraint(condition=models.Q(sick_hours__range=(0, 24)), name='sick_hours_range'),
            models.CheckConstraint(condition=models.Q(holiday_hours__range=(0, 24)), name='holiday_hours_range'),
            models.CheckConstraint(condition=models.Q(leave_hours__range=(0, 24)), name='leave_hours_range'),
            models.CheckConstraint(
                condition=models.Q(special_leave_hours__range=(0, 24)), name='special_leave_hours_range'
            ),
            models.CheckConstraint(
                condition=models.Q(night_shift_hours__range=(0, NIGHTTIME_WORK_HOURS_MAX)),
                name='night_shift_hours_range',
            ),
            models.CheckConstraint(condition=models.Q(on_call_hours__range=(0, 24)), name='on_call_hours_range'),
            models.CheckConstraint(condition=models.Q(travel_hours__range=(0, 24)), name='travel_hours_range'),
            models.CheckConstraint(condition=models.Q(rest_hours__range=(0, 24)), name='rest_hours_range'),
            models.CheckConstraint(condition=models.Q(bank_to__range=(0, 24)), name='bank_to_range'),
            models.CheckConstraint(condition=models.Q(bank_from__range=(0, 24)), name='bank_from_range'),
        ]

    @override
    def __str__(self) -> str:
        return f'{self.date}: {self.resource} on "{self.task}"'

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
        return Decimal(self.day_shift_hours) + Decimal(self.night_shift_hours) + Decimal(self.travel_hours)

    @property
    def total_hours(self) -> Decimal:
        """Compute the grand total of all hours logged on this entry.

        This includes hours logged as absence and hours deposited/withdrawn from bank.

        :return: the computed total.
        """
        # NOTE: see `total_task` hours, the same applies here
        return (
            self.total_task_hours
            + Decimal(self.leave_hours)
            + Decimal(self.special_leave_hours)
            + Decimal(self.sick_hours)
            + Decimal(self.holiday_hours)
            + Decimal(self.rest_hours)
            + Decimal(self.bank_from)
            - Decimal(self.bank_to)
        )

    @property
    def is_submitted(self) -> bool:
        return not (self.timesheet is None or self.timesheet.closed is False)

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
    def is_rest(self) -> bool:
        return self.rest_hours > 0.0

    @property
    def is_special_leave(self) -> bool:
        return self.special_leave_reason is not None

    @property
    def has_day_entry_hours(self) -> bool:
        return self.is_sick_day or self.is_holiday or self.is_leave or self.is_special_leave or self.is_rest

    @property
    def is_task_entry(self) -> bool:
        return not self.is_day_entry

    @property
    def has_task_entry_hours(self) -> bool:
        return self.total_task_hours > 0.0 or self.on_call_hours > 0.0

    @property
    def does_entry_blocking_overtime_exist_for_same_day(self) -> bool:
        time_entries_for_same_day = TimeEntry.objects.filter(resource=self.resource, date=self.date).exclude(pk=self.pk)
        for time_entry in time_entries_for_same_day:
            if time_entry.is_leave or time_entry.is_special_leave or time_entry.is_rest:
                return True
        return False

    @property
    def net_bank_hours(self) -> Decimal:
        """Calculate net bank hour change for this entry."""
        return Decimal(self.bank_from) - Decimal(self.bank_to)

    @property
    def special_hours(self) -> Decimal:
        """Return the total hours spent on "special activities".

        Special activities include:
        - special leave
        - sick day
        - holiday
        """
        return Decimal(self.special_leave_hours) + Decimal(self.sick_hours) + Decimal(self.holiday_hours)

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
            self._verify_timesheet_not_submitted,
            self._verify_task_hours_not_logged_in_day_entry,
            self._verify_day_hours_not_logged_in_task_entry,
            self._verify_task_and_day_hours_not_logged_together,
            self._verify_at_most_one_absence,
            self._verify_honors_total_hours_restrictions,
            self._verify_reason_only_on_special_leave,
            self._verify_special_leave_reason_is_valid,
            self._verify_no_overtime_with_leave_or_rest_entry,
            self._verify_bank_hours_not_both_directions,
            self._verify_bank_hours_balance_limits,
            self._verify_bank_hours_restrictions_with_day_entries,
            self._verify_bank_hours_against_scheduled_hours,
            self._verify_protocol_number,
        )

        for validator in validators:
            try:
                validator()
            except ValidationError as e:
                errors.append(e)

        if errors:
            raise ValidationError(errors)

    def _verify_timesheet_not_submitted(self) -> None:
        if self.resource_id and self.date:
            submitted = TimesheetSubmission.objects.filter(
                resource=self.resource,
                closed=True,
                period__contains=self.date
            ).exists()

            if submitted:
                raise ValidationError(
                    _('Cannot modify time entries for submitted timesheets'),
                    code='timesheet_submitted'
                )

    def _verify_protocol_number(self) -> None:
        if self.protocol_number and not self.is_sick_day:
            raise ValidationError(
                _('Protocol number can be used only for sick days'), code='protocol_number_without_sick_day'
            )
        if self.protocol_number and not self.protocol_number.isdigit():
            raise ValidationError(_('Protocol number digits must be numeric'), code='protocol_number_not_numeric')

    def _verify_task_hours_not_logged_in_day_entry(self) -> None:
        if self.is_day_entry and self.has_task_entry_hours:
            raise ValidationError(_('You cannot log task hours in a day entry'), code='task_hours_in_day_entry')

    def _verify_day_hours_not_logged_in_task_entry(self) -> None:
        if self.is_task_entry and self.has_day_entry_hours:
            raise ValidationError(_('You cannot log non-task hours in a task entry'), code='day_hours_in_task_entry')

    def _verify_at_most_one_absence(self) -> None:
        is_one_of_the_leave_types = self.is_leave or self.is_special_leave
        has_too_many_day_entry_hours_logged = (
            len([cond for cond in (self.is_sick_day, self.is_holiday, is_one_of_the_leave_types) if cond]) > 1
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

    def _verify_honors_total_hours_restrictions(self) -> None:
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
        if total_hours_on_same_day > (DAYTIME_WORK_HOURS_MAX + NIGHTTIME_WORK_HOURS_MAX):
            raise ValidationError(
                _('Total hours on all time entries on {date} ({total_hours}) is over 24 hours').format(
                    date=self.date, total_hours=total_hours_on_same_day
                ),
                code='too_much_total_time_logged',
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
        if self.special_leave_reason is None:
            raise ValidationError(
                _('reason is required'),
                code='missing_special_leave_reason',
            )
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

        if not (
            self.does_entry_blocking_overtime_exist_for_same_day
            or self.is_special_leave
            or self.is_rest
            or self.is_leave
        ):
            return

        total_hours_on_same_day = sum(entry.total_hours for entry in other_entries_on_same_day) + self.total_hours
        scheduled_hours = self.resource.scheduled_working_hours_for_day(KrmDay(self.date))

        if total_hours_on_same_day > scheduled_hours:
            raise ValidationError(
                _(
                    'No overtime allowed when logging a {kind}. Maximum allowed is {work_hours}, got {actual_hours}'
                ).format(
                    kind='rest' if self.is_rest else 'leave',
                    work_hours=scheduled_hours,
                    actual_hours=total_hours_on_same_day,
                ),
                code='overtime_while_resting_or_on_leave',
            )

    def _verify_bank_hours_not_both_directions(self) -> None:
        """Verify that we don't have both withdrawal and deposit on the same day."""
        if self.bank_from > 0.0 and self.bank_to > 0.0:
            raise ValidationError(
                _('Cannot both withdraw from and deposit to bank hours on the same day'), code='bank_both_directions'
            )

    def _verify_bank_hours_balance_limits(self) -> None:
        """Verify that the transaction won't exceed total balance limits (-16 to +16)."""
        balance_upper = Decimal(str(config.BANK_HOURS_UPPER_BOUND))
        balance_lower = Decimal(str(config.BANK_HOURS_LOWER_BOUND))
        current_balance = self.resource.get_bank_hours_balance()
        new_balance = current_balance + self.bank_to - self.bank_from

        if new_balance > balance_upper:
            raise ValidationError(
                _(
                    'This transaction would exceed the maximum bank balance of {limit} hours. '
                    'Current balance: {current}, attempting to add: {change}'
                ).format(limit=balance_upper, current=current_balance, change=self.net_bank_hours),
                code='bank_balance_exceeds_upper_limit',
            )
        if new_balance < balance_lower:
            raise ValidationError(
                _(
                    'This transaction would exceed the minimum bank balance of {limit} hours. '
                    'Current balance: {current}, attempting to change by: {change}'
                ).format(limit=balance_lower, current=current_balance, change=self.net_bank_hours),
                code='bank_balance_exceeds_lower_limit',
            )

    def _verify_bank_hours_restrictions_with_day_entries(self) -> None:
        """Verify bank hours restrictions with different types of day entries."""
        if (self.is_holiday or self.is_sick_day) and (self.bank_to > 0.0 or self.bank_from > 0.0):
            raise ValidationError(
                _('Cannot use bank hours during holidays or sick days'), code='bank_hours_not_allowed_on_holidays'
            )

        day_entry_types_no_deposits = self.is_leave or self.is_rest or self.is_special_leave
        if day_entry_types_no_deposits and self.bank_to > 0.0:
            day_type = 'leave' if self.is_leave else 'rest' if self.is_rest else 'special leave'
            raise ValidationError(
                _('Cannot deposit bank hours during a {day_type}').format(day_type=day_type),
                code='bank_deposits_not_allowed_on_day_entries',
            )

    def _verify_bank_hours_against_scheduled_hours(self) -> None:
        """Verify bank hours usage against scheduled hours for task entries."""
        if not self.is_day_entry:
            return

        all_entries = TimeEntry.objects.filter(date=self.date, resource=self.resource)
        total_hours_on_same_day = sum(entry.total_hours for entry in all_entries)
        total_hours_with_bank_hours = total_hours_on_same_day + self.net_bank_hours
        schedule = self.resource.get_schedule(self.date, self.date + datetime.timedelta(days=1))
        scheduled_hours = schedule[self.date]
        if scheduled_hours is None:
            return

        if scheduled_hours >= 0 and total_hours_with_bank_hours < scheduled_hours and self.bank_to > 0.0:
            raise ValidationError(
                _(
                    'Cannot deposit {bank_hours} bank hours. Total hours would become {task_hours} '
                    'which is below scheduled hours ({scheduled_hours})'
                ).format(
                    bank_hours=self.bank_to, task_hours=total_hours_with_bank_hours, scheduled_hours=scheduled_hours
                ),
                code='bank_deposit_below_scheduled_hours',
            )

        if total_hours_with_bank_hours > scheduled_hours and self.bank_from > 0.0:
            raise ValidationError(
                _(
                    'Cannot withdraw bank hours when task hours ({task_hours}) are higher or equal scheduled hours'
                    ' ({scheduled_hours})'
                ).format(task_hours=total_hours_with_bank_hours, scheduled_hours=scheduled_hours),
                code='bank_withdraw_above_scheduled_hours',
            )

@receiver(models.signals.pre_save, sender=TimeEntry)
def clear_sick_day_or_holiday_entry_on_same_day(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    entries = cast('TimeEntryQuerySet', TimeEntry.objects).filter(date=instance.date, resource=instance.resource)
    if instance.is_task_entry:
        overwritten = entries.sick_days_and_holidays()
    elif instance.is_day_entry:
        # just to be safe: remove any other existing day entry
        overwritten = entries.day_entries().exclude(pk=instance.pk)
    else:
        # we should never get there
        overwritten = TimeEntry.objects.none()
    overwritten.delete()

@receiver(models.signals.post_delete, sender=TimeEntry)
def clear_bank_hours_when_no_work(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    """Auto-clear bank deposits if there are no work hours."""
    entries = cast('TimeEntryQuerySet', TimeEntry.objects).filter(date=instance.date, resource=instance.resource)
    bank_to_entry = entries.filter(bank_to__gt=0).first()
    total_task_hours = sum(entry.total_task_hours for entry in entries)
    schedule = instance.resource.get_schedule(instance.date, instance.date + datetime.timedelta(days=1))
    scheduled_hours = schedule[instance.date]
    if instance.is_task_entry and total_task_hours < scheduled_hours and bank_to_entry:
        bank_to_entry.bank_to = 0
        bank_to_entry.save()

@receiver(models.signals.pre_save, sender=TimeEntry)
def clear_task_entries_on_same_day(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    entries = cast('TimeEntryQuerySet', TimeEntry.objects).filter(date=instance.date, resource=instance.resource)
    if instance.is_sick_day or instance.is_holiday:
        overwritten = entries.task_entries()
    elif instance.is_task_entry:
        # just to be safe: remove any other existing task entry for the
        # `instance`'s task
        overwritten = entries.filter(task=instance.task).exclude(pk=instance.pk)
    else:
        overwritten = TimeEntry.objects.none()
    overwritten.delete()


@receiver(models.signals.post_save, sender=TimesheetSubmission)
def link_entries(sender: TimesheetSubmission, instance: TimesheetSubmission | list | tuple, **kwargs: Any) -> None:
    instance.timeentry_set.update(timesheet=None)
    if isinstance(instance.period, (list | tuple)):
        lower, upper = instance.period[0], instance.period[1]
    else:
        lower, upper = instance.period.lower, instance.period.upper
    TimeEntry.objects.filter(resource=instance.resource, date__gte=lower, date__lt=upper).update(timesheet=instance)


@receiver(models.signals.pre_save, sender=TimeEntry)
def link_to_timesheet(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    timesheet = TimesheetSubmission.objects.filter(resource=instance.resource, period__contains=instance.date).first()
    instance.timesheet = timesheet


class ExtraHoliday(models.Model):
    period = DateRangeField(help_text=_('N.B.: End date is the day after the actual end date'))
    # see https://holidays.readthedocs.io/en/latest/
    country_codes = ArrayField(
        models.CharField(help_text=_('holidays.code and optionally subdivision from holidays library'))
    )
    reason = models.CharField()

    def __str__(self) -> str:
        reason = shorten(self.reason, width=30, placeholder=' ...')
        end_dt = self.period.upper - datetime.timedelta(days=1)
        if self.period.lower == end_dt:
            return f'{self.period.lower.strftime("%Y-%m-%d")}: {reason}'
        return f'{self.period.lower.strftime("%Y-%m-%d")} - {end_dt.strftime("%Y-%m-%d")}: {reason}'

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        if self.period.upper < self.period.lower + datetime.timedelta(days=1):
            raise ValidationError({'period': 'End date must be at least one day after start date.'})
