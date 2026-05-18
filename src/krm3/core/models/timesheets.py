from __future__ import annotations

import datetime
from decimal import Decimal as D  # noqa: N817
from textwrap import shorten
from typing import TYPE_CHECKING, Any, Iterable, Self, override

from constance import config
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import ArrayField, DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, QuerySet
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from krm3.utils.dates import KrmDay
from krm3.utils.models import CleanValidatorsMixin

from ...timesheet.operations import DayEntryProcessor
from ...utils.numbers import safe_dec
from .auth import Resource

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from django.db.models.base import ModelBase

    from krm3.core.models import TaskEntry

DAYTIME_WORK_HOURS_MAX = 16
NIGHTTIME_WORK_HOURS_MAX = 8


class SpecialLeaveReasonQuerySet(QuerySet):
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
            raise ValidationError(_('End date must be at least one day after start date'), code='invalid_date_interval')
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
    def save(
        self,
        *,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:  # noqa: D102, ANN001
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
        timesheet = TimesheetDTO().fetch(self.resource, lower, upper)
        return TimesheetSerializer(timesheet).data


def acl_queryset_factory(prefix: str) -> QuerySet:

    class TimeEntriesQuerySet(QuerySet):
        def open(self) -> Self:
            """Select the open time entries in this queryset.

            :return: the filtered queryset.
            """
            return self.filter(
                Q(**{f'{prefix}timesheet__isnull': True})
                | Q(**{f'{prefix}timesheet__closed': False})
            )

        def closed(self) -> Self:
            """Select the closed time entries in this queryset.

            :return: the filtered queryset.
            """
            return self.filter(
                **{f'{prefix}timesheet__isnull': False, f'{prefix}timesheet__closed': True}
            )

        def filter_acl(self, user: AbstractUser) -> Self:
            """Return the queryset for the owned records.

            Superuser gets them all.
            """
            if user.is_superuser or user.get_all_permissions().intersection(
                {'core.manage_any_timesheet', 'core.view_any_timesheet'}
            ):
                return self.all()
            return self.filter(**{f'{prefix}resource__user': user})

    return TimeEntriesQuerySet

TaskEntriesQuerySet: QuerySet[TaskEntry] = acl_queryset_factory(prefix='day_entry__')
DayEntriesQuerySet: QuerySet[DayEntry] = acl_queryset_factory(prefix='')

class DayEntry(CleanValidatorsMixin, models.Model):
    """A day entry for a Resource under contract."""

    day = models.DateField(help_text=_('Day'))
    last_modified = models.DateTimeField(auto_now=True)
    closed = models.BooleanField(default=False, help_text=_('Submitted'))
    comment = models.TextField(null=True, blank=True, help_text=_('Notes'))
    contract = models.ForeignKey("Contract", on_delete=models.PROTECT)
    timesheet = models.ForeignKey(TimesheetSubmission, on_delete=models.SET_NULL, null=True, blank=True)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT, help_text=_('Resource'))

    bank = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.0, help_text=_('Hours bank, positive deposits, negative withdrawals')
    )

    # Denormalised from contract
    due_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, help_text=_('Due hours for the day'))

    # Denormalised from children TaskDay
    travel_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, help_text=_('Travel hours'))
    day_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, help_text=_('Day shift hours'))
    night_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, help_text=_('Night shift hours'))
    on_call_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, help_text=_('On call hours'))

    is_holiday = models.BooleanField(
        default=False, help_text=_("Is Holiday for resource according to contract's calendar")
    )
    asked_holiday = models.BooleanField(default=False, help_text=_('Holiday requested by resource'))
    leave_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, help_text=_('Leave hours'))
    special_leave_hours = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.0, help_text=_('Special leave hours')
    )
    special_leave_reason = models.ForeignKey(
        SpecialLeaveReason, on_delete=models.PROTECT, null=True, blank=True, help_text=_('Special leave reason')
    )
    protocol_number = models.CharField(null=True, blank=True, help_text=_('Sick certificate number'))
    is_sick = models.BooleanField(default=False, help_text=_('Resource called in sick'))
    rest_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0, help_text=_('Rest hours'))
    overtime_hours = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.0, help_text=_('Overtime hours in the day')
    )
    meal_voucher = models.PositiveIntegerField(default=0, help_text=_('Meal voucher for the day'))

    objects = DayEntriesQuerySet.as_manager()

    class Meta:
        verbose_name_plural = 'Day entries'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(special_leave_hours__range=(0, 24)), name='special_leave_hours_range'
            ),
            models.CheckConstraint(condition=models.Q(leave_hours__range=(0, 24)), name='leave_hours_range'),
            models.CheckConstraint(condition=models.Q(bank__range=(-8, 8)), name='bank_range'),
            models.CheckConstraint(condition=models.Q(rest_hours__range=(0, 24)), name='rest_hours_range'),
        ]

    def __str__(self) -> str:
        return f'{self.resource} - {self.day}'

    @property
    def bank_from(self):
        return -1 * self.bankb if self.bank < 0 else 0

    @property
    def bank_to(self):
        return self.bank if self.bank > 0 else 0

    @property
    def nwd(self) -> bool:
        """Return True if the day is a non-working day."""
        return self.is_holiday or self.due_hours == 0

    def reset(self, full: bool = False, **kwargs) -> None:
        """
        Reset the day entry to initial values except for Contract, Resource, Comment, and day, that are left unchanged.

        If Comment is provided, it will override the existing comment.

        If full is False [default], only the fields calculated from the related TimeEntries are reset.
        """
        self.closed = self.timesheet.closed if self.timesheet else False
        self.is_holiday = self.contract.is_holiday(self.day)
        self.due_hours = self.contract.get_due_hours(self.day)
        self.overtime_hours = D(0.0)
        self.meal_voucher = 0
        self.taskentry_set.set(kwargs.pop('task_entries', []))

        self.travel_hours = D(0.0)
        self.day_hours = D(0.0)
        self.night_hours = D(0.0)
        self.on_call_hours = D(0.0)

        self.comment = kwargs.pop('comment', self.comment)

        if full:  # reset also non-calculated fields
            self.bank_hours = D(0.0)
            self.asked_holiday = False
            self.leave_hours = D(0.0)
            self.special_leave_hours = D(0.0)
            self.special_leave_reason = None
            self.protocol_number = None
            self.is_sick = False
            self.rest_hours = D(0.0)

    def refresh(self, task_entries: Iterable[TaskEntry] | None, drop_existing=True) -> None:
        """Recalculate the day entry based on the given task entries.

        Invokes clean() after the calculation.
        If drop_existing is True, existing TaskEntries are removed before recalculating.
        If task_entries is None, all children TaskEntries existing in the DB are used.
        """
        if drop_existing:
            self.taskentry_set.all().delete()

        if task_entries is None:
            task_entries = list(self.taskentry_set.all())

        self.day_hours = D(sum([safe_dec(te.day_shift_hours) for te in task_entries]))
        self.night_hours = D(sum([safe_dec(te.night_shift_hours) for te in task_entries]))
        self.travel_hours = D(sum([safe_dec(te.travel_hours) for te in task_entries]))
        self.on_call_hours = D(sum([safe_dec(te.on_call_hours) for te in task_entries]))

        if meal_threshold := self.contract.meal_threshold(self.day):
            self.meal_voucher = 1 if self.worked_hours >= meal_threshold else 0
        else:
            self.meal_voucher = 0

        if self.contract.overtime:
            overtime = self.worked_hours - self.due_hours
            self.overtime_hours = overtime if overtime > 0 else D(0.0)
        else:
            self.overtime_hours = 0

        self.clean()

    def add_task_entry(self, task_entry: TaskEntry | None = None, **kwargs) -> DayEntry:
        """Add a single TaskEntry to the DayEntry using the DayEntryProcessor and refreshes."""
        dp = DayEntryProcessor(resource=self.resource, day=self.day, contract=self.contract)

        if task_entry is None:
            return dp.add_task_entry(day_entry=self, **kwargs)
        if kwargs:
            raise ValueError(_('Cannot have both task_entry and kwargs'))
        return dp.add_task_entry(task_entry=task_entry, day_entry=self, **kwargs)

    def del_task_entry(self, task_or_entry: 'int | TaskEntry | Task') -> 'DayEntry':
        """Delete a single TaskEntry from the DayEntry using the DayEntryProcessor and refreshes."""
        dp = DayEntryProcessor(resource=self.resource, day=self.day, contract=self.contract)
        return dp.del_task_entry(task_or_entry=task_or_entry)

    @property
    def worked_hours(self):
        """The sum of Day Shift + Night Shift + Travel Hours recorded in the TaskEntries."""
        return self.day_hours + self.night_hours + self.travel_hours

    @property
    def regular_hours(self):
        return D(min(self.worked_hours - D(self.bank), self.due_hours))

    @property
    def remaining_hours(self):
        hours = self.due_hours - self.regular_hours
        return max(0, hours)

    @property
    def is_leave(self) -> bool:
        return self.leave_hours > 0

    @property
    def is_special_leave(self) -> bool:
        return self.special_leave_hours > 0

    @property
    def is_rest(self) -> bool:
        return self.rest_hours > 0

    def _verify_bank_hours_balance_limits(self) -> None:
        """Verify that the transaction won't exceed total balance limits (-16 to +16)."""
        balance_upper = D(str(config.BANK_HOURS_UPPER_BOUND))
        balance_lower = D(str(config.BANK_HOURS_LOWER_BOUND))
        current_balance = self.resource.get_bank_hours_balance(self.day)
        new_balance = current_balance + D(self.bank)

        if new_balance > balance_upper:
            raise ValidationError(
                _(
                    'This transaction would exceed the maximum bank balance of {limit} hours. '
                    'Current balance: {current}, attempting to add: {change}'
                ).format(limit=balance_upper, current=current_balance, change=self.bank),
                code='bank_balance_exceeds_upper_limit',
            )
        if new_balance < balance_lower:
            raise ValidationError(
                _(
                    'This transaction would exceed the minimum bank balance of {limit} hours. '
                    'Current balance: {current}, attempting to change by: {change}'
                ).format(limit=balance_lower, current=current_balance, change=self.bank),
                code='bank_balance_exceeds_lower_limit',
            )

    def _verify_timesheet_not_submitted(self) -> None:
        if self.timesheet and self.timesheet.closed:
            raise ValidationError(_('Cannot modify entries for submitted timesheets'), code='timesheet_submitted')

    def _verify_bank_hours_restrictions_with_day_entries(self) -> None:
        """Verify bank hours restrictions with different types of day entries."""
        if self.bank != 0.0 and (self.is_holiday or self.asked_holiday or self.is_sick):
            raise ValidationError(
                _('Cannot use bank hours during holidays or sick days'), code='bank_hours_not_allowed_on_holidays'
            )

        day_entry_types_no_deposits = self.is_leave or self.is_rest or self.is_special_leave
        if day_entry_types_no_deposits and self.bank > 0.0:
            day_type = 'leave' if self.is_leave else 'rest' if self.is_rest else 'special leave'
            raise ValidationError(
                _('Cannot deposit bank hours during a {day_type}').format(day_type=day_type),
                code='bank_deposits_not_allowed_on_day_entries',
            )

    # def _verify_bank_hours_against_scheduled_hours(self) -> None:
    #     """Verify bank hours usage against scheduled hours for task entries."""
    #     all_entries = TaskEntry.objects.filter(date=self.day, resource=self.resource)
    #     total_hours_on_same_day = sum(entry.total_hours for entry in all_entries)
    #     total_hours_with_bank_hours = total_hours_on_same_day - self.bank
    #     schedule = self.resource.get_schedule(self.day, self.day + datetime.timedelta(days=1))
    #     scheduled_hours = schedule[self.day]
    #     if scheduled_hours is None:
    #         return
    #
    #     if scheduled_hours >= 0 and total_hours_with_bank_hours < scheduled_hours and self.bank > 0.0:
    #         raise ValidationError(
    #             _(
    #                 'Cannot deposit {bank_hours} bank hours. Total hours would become {task_hours} '
    #                 'which is below scheduled hours ({scheduled_hours})'
    #             ).format(
    #                 bank_hours=self.bank, task_hours=total_hours_with_bank_hours, scheduled_hours=scheduled_hours
    #             ),
    #             code='bank_deposit_below_scheduled_hours',
    #         )
    #
    #     if total_hours_with_bank_hours > scheduled_hours and self.bank < 0.0:
    #         raise ValidationError(
    #             _(
    #                 'Cannot withdraw bank hours when task hours ({task_hours}) are higher or equal scheduled hours'
    #                 ' ({scheduled_hours})'
    #             ).format(task_hours=total_hours_with_bank_hours, scheduled_hours=scheduled_hours),
    #             code='bank_withdraw_above_scheduled_hours',
    #         )

    def _verify_protocol_number(self) -> None:
        if self.protocol_number and not self.is_sick:
            raise ValidationError(
                _('Protocol number can be used only for sick days'), code='protocol_number_without_sick_day'
            )
        if self.protocol_number and not self.protocol_number.isdigit():
            raise ValidationError(_('Protocol number digits must be numeric'), code='protocol_number_not_numeric')

    def _verify_at_most_one_absence(self) -> None:
        is_one_of_the_leave_types = self.is_leave or self.is_special_leave
        has_too_many_day_entry_hours_logged = (
            len([cond for cond in (self.is_sick, self.is_holiday, is_one_of_the_leave_types) if cond]) > 1
        )
        if has_too_many_day_entry_hours_logged:
            raise ValidationError(
                _('You cannot log more than one kind of non-task hours in a day'),
                code='multiple_absence_kind',
            )


class TaskEntry(CleanValidatorsMixin, models.Model):
    """A timesheet task-related entry."""

    day_shift_hours = models.DecimalField(max_digits=4, decimal_places=2)
    night_shift_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    on_call_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    travel_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    comment = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, null=True, blank=True)

    task = models.ForeignKey('Task', on_delete=models.PROTECT, related_name='task_entries')

    # this will need to be turned into not nullable after migrations
    day_entry = models.ForeignKey(DayEntry, on_delete=models.CASCADE)

    objects = TaskEntriesQuerySet.as_manager()

    class Meta:
        verbose_name_plural = 'Task entries'
        permissions = [
            ('view_any_timesheet', "Can view(only) everybody's timesheets"),
            ('manage_any_timesheet', "Can view, and manage everybody's timesheets"),
        ]
        constraints = [
            models.UniqueConstraint(fields=('day_entry', 'task'), name='unique_day_entry_task'),
            models.CheckConstraint(
                condition=models.Q(day_shift_hours__range=(0, DAYTIME_WORK_HOURS_MAX)), name='day_shift_hours_range'
            ),
            models.CheckConstraint(
                condition=models.Q(night_shift_hours__range=(0, NIGHTTIME_WORK_HOURS_MAX)),
                name='night_shift_hours_range',
            ),
            models.CheckConstraint(condition=models.Q(on_call_hours__range=(0, 24)), name='on_call_hours_range'),
            models.CheckConstraint(condition=models.Q(travel_hours__range=(0, 24)), name='travel_hours_range'),
        ]

    @override
    def __str__(self) -> str:
        return f'{self.day_entry.day}: {self.day_entry.resource} on "{self.task}"'

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
    def total_task_hours(self) -> D:
        """Compute the total task-related hours logged on this entry.

        :return: the computed total.
        """
        # NOTE: could use sum() on a comprehension, but `sum()` may also
        #       return Literal[0], which trips up the type checker
        return D(self.day_shift_hours) + D(self.night_shift_hours) + D(self.travel_hours)

    @property
    def is_submitted(self) -> bool:
        return not (self.day_entry.timesheet is None or self.day_entry.timesheet.closed is False)

    def _verify_timesheet_not_submitted(self) -> None:
        if self.pk is None:
            return
        if self.is_submitted or (
            TimesheetSubmission.objects.filter(
                resource=self.day_entry.resource, closed=True, period__contains=self.day_entry.day
            ).exists()
        ):
            raise ValidationError(_('Cannot modify time entries for submitted timesheets'), code='timesheet_submitted')

    def _verify_no_negative_hours(self) -> None:
        if any(
            field < 0
            for field in (
                self.day_shift_hours,
                self.night_shift_hours,
                self.travel_hours,
                self.on_call_hours,
            )
        ):
            raise ValidationError(_('All hours must be 0 or greater'), code='negative_hours')

    def _verify_at_least_one_nonzero_hours_and_bank_field(self) -> None:
        hours_fields = (
            self.day_shift_hours,
            self.night_shift_hours,
            self.travel_hours,
            self.on_call_hours,
        )
        if all(field == 0 for field in hours_fields):
            raise ValidationError(_('At least one hours or bank field must be greater than 0'), code='all_zero_hours')

    # def _verify_task_hours_not_logged_in_day_entry(self) -> None:
    #     if self.is_day_entry and self.has_task_entry_hours:
    #         raise ValidationError(_('You cannot log task hours in a day entry'), code='task_hours_in_day_entry')

    # def _verify_honors_total_hours_restrictions(self) -> None:
    #     if self.total_hours > 24:
    #         raise ValidationError(
    #             _('Total hours on this time entry ({total_hours}) is over 24 hours').format(
    #                 date=self.date, total_hours=self.total_hours
    #             ),
    #             code='too_much_total_time_logged',
    #         )
    #
    #     # we might be overwriting an existing time entry on the same
    #     # task (even None) - exclude it, as it should no longer count
    #     entries_on_same_day = self.__class__.objects.filter(date=self.date, resource=self.resource).exclude(
    #         task=self.task
    #     )
    #
    #     total_hours_on_same_day = sum(entry.total_hours for entry in entries_on_same_day) + self.total_hours
    #     if total_hours_on_same_day > (DAYTIME_WORK_HOURS_MAX + NIGHTTIME_WORK_HOURS_MAX):
    #         raise ValidationError(
    #             _('Total hours on all time entries on {date} ({total_hours}) is over 24 hours').format(
    #                 date=self.date, total_hours=total_hours_on_same_day
    #             ),
    #             code='too_much_total_time_logged',
    #         )

    # def _verify_reason_only_on_special_leave(self) -> None:
    #     if self.day_entry.special_leave_reason and not self.day_entry.special_leave_hours:
    #         raise ValidationError(_('Only a special leave can have a reason'), code='reason_on_non_special_leave')
    #     if not self.day_entry.special_leave_reason and self.day_entry.special_leave_hours:
    #         raise ValidationError(
    #             _('Reason is required when logging a special leave'), code='no_reason_on_special_leave'
    #         )

    # def _verify_special_leave_reason_is_valid(self) -> None:
    #     if not self.is_special_leave:
    #         return
    #     if self.special_leave_reason is None:
    #         raise ValidationError(
    #             _('reason is required'),
    #             code='missing_special_leave_reason',
    #         )
    #     if not self.special_leave_reason.is_valid(self.date):
    #         raise ValidationError(
    #             _('Reason "{title}" is not valid on {date}').format(
    #                 title=self.special_leave_reason.title, date=self.date
    #             ),
    #             code='invalid_special_leave_reason',
    #         )

    # def _verify_no_overtime_with_leave_or_rest_entry(self) -> None:
    #     # we might be overwriting an existing time entry on the same
    #     # task (even None) - exclude it, as it should no longer count
    #     # if we're updating the model directly, the current row on the
    #     # db should not count as well because we're replacing it
    #     all_entries = cast('TaskEntryQuerySet', TaskEntry.objects.filter(date=self.date, resource=self.resource))
    #
    #     other_entries_on_same_day = all_entries.exclude(task=self.task).exclude(pk=self.pk)
    #
    #     if not (
    #             self.does_entry_blocking_overtime_exist_for_same_day
    #             or self.is_special_leave
    #             or self.is_rest
    #             or self.is_leave
    #     ):
    #         return
    #
    #     total_hours_on_same_day = sum(entry.total_hours for entry in other_entries_on_same_day) + self.total_hours
    #     scheduled_hours = self.resource.scheduled_working_hours_for_day(KrmDay(self.date))
    #
    #     if total_hours_on_same_day > scheduled_hours:
    #         raise ValidationError(
    #             _(
    #                 'No overtime allowed when logging a {kind}. Maximum allowed is {work_hours}, got {actual_hours}'
    #             ).format(
    #                 kind='rest' if self.is_rest else 'leave',
    #                 work_hours=scheduled_hours,
    #                 actual_hours=total_hours_on_same_day,
    #             ),
    #             code='overtime_while_resting_or_on_leave',
    #         )


@receiver(models.signals.post_save, sender=TimesheetSubmission)
def link_entries(sender: TimesheetSubmission, instance: TimesheetSubmission | list | tuple, **kwargs: Any) -> None:
    instance.dayentry_set.update(timesheet=None)
    if isinstance(instance.period, (list | tuple)):
        lower, upper = instance.period[0], instance.period[1]
    else:
        lower, upper = instance.period.lower, instance.period.upper
    DayEntry.objects.filter(resource=instance.resource, day__gte=lower, day__lt=upper).update(timesheet=instance)


@receiver(models.signals.pre_save, sender=DayEntry)
def link_to_timesheet(sender: DayEntry, instance: DayEntry, **kwargs: Any) -> None:
    timesheet = TimesheetSubmission.objects.filter(resource=instance.resource, period__contains=instance.day).first()
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
        if self.period.upper is None or self.period.lower is None:
            raise ValidationError({'period': _('Open-ended period not supported')})
        if self.period.upper < self.period.lower + datetime.timedelta(days=1):
            raise ValidationError({'period': _('End date must be at least one day after start date')})
