import datetime
import json
from decimal import Decimal as D  # noqa: N817
from functools import cached_property
from typing import TYPE_CHECKING, Iterable, Self

from cachetools import cachedmethod
from constance import config
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from krm3.config import settings
from krm3.core.storage import PrivateMediaStorage
from krm3.missions.media import contract_directory_path
from krm3.timesheet.operations import DayEntryProcessor
from krm3.types.krmdates import MaybeKrmDayType
from krm3.utils.dates import DATE_INFINITE, KrmDay, get_country_holidays, KrmDateRange

if TYPE_CHECKING:
    from krm3.core.models import Contract, DayEntry, Resource, Task, TaskEntry
    from krm3.core.models.auth import User


class ContractQuerySet(models.QuerySet['Contract']):
    def active_between(self, start: datetime.date, end: datetime.date) -> Self:
        """Return the contracts valid in the given interval.

        :param start: the start of the interval (inclusive).
        :param end: the end of the interval (inclusive).
        :return: the filtered `Contract`s.
        """
        end = end + datetime.timedelta(days=1)
        return self.filter(period__overlap=(start, end))

    def filter_acl(self, user: "User") -> Self:
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.has_any_perm('core.view_any_contract', 'core.manage_any_contract'):
            return self.all()
        return self.filter(resource__user=user)

    def by_day_range(self, resource: 'Resource', lower: MaybeKrmDayType, upper: MaybeKrmDayType) -> Self:
        """Return contracts for the given resource day_range.

        Thw day_range must be closed-open range (upper boundary excluded).
        """
        period = KrmDateRange(lower, upper)
        qs = self.filter(resource=resource, period__overlap=period)
        periods: list[KrmDateRange] = list(
            map(lambda x: KrmDateRange(x.lower, x.upper).as_dates(), qs.values_list('period', flat=True))
        )
        match len(periods):
            case 0:
                raise ValueError(_('No contract found in range'))
            case 1:
                if not periods[0].contains(period):
                    raise ValueError(_('Contract cover missing for requested range'))
            case _:
                for i, period_found in enumerate(periods[:-1]):
                    if not period_found.precedes(periods[i + 1]):
                        raise ValueError(_('Contract cover missing for requested range'))
        return qs

    def by_day(self, resource: 'Resource', day: datetime.date | KrmDay) -> 'Contract | None':
        """Return contract for the given resource and day."""
        return self.filter(resource=resource, period__contains=KrmDay(day).date).first()


class Contract(models.Model):
    resource = models.ForeignKey('core.Resource', on_delete=models.PROTECT)
    period = DateRangeField(help_text=_('N.B.: End date is the day after the actual end date'))
    country_calendar_code = models.CharField(
        null=True,
        blank=True,
        help_text='Country calendar code as per https://holidays.readthedocs.io/en/latest/#available-countries',
    )
    working_schedule = models.JSONField(blank=True, default=dict)
    meal_voucher = models.JSONField(blank=True, default=dict)
    comment = models.TextField(null=True, blank=True, help_text='Optional comment about the contract')
    document = models.FileField(
        upload_to=contract_directory_path,
        storage=PrivateMediaStorage(),
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf'])],
        help_text='Optional PDF document (PDF files only)',
    )
    sunday_as_holiday = models.BooleanField(default=True, help_text=_('Sunday always a holiday'))
    overtime = models.BooleanField(default=True, help_text=_('Is overtime tracked'))

    objects = ContractQuerySet.as_manager()

    class Meta:
        ordering = ('period',)
        constraints = [
            ExclusionConstraint(
                name='exclude_overlapping_contracts',
                expressions=[
                    ('period', RangeOperators.OVERLAPS),
                    ('resource', RangeOperators.EQUAL),
                ],
            )
        ]
        permissions = [
            ('view_any_contract', "Can view(only) everybody's contracts"),
            ('manage_any_contract', "Can view, and manage everybody's contracts"),
        ]

    def __str__(self) -> str:
        upper = f'{(self.period.upper - datetime.timedelta(days=1)):%Y-%m-%d}' if self.period.upper else '...'
        return f'{self.resource}, {self.period.lower:%Y-%m-%d} - {upper}'

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()

        if self.period.lower is None:
            raise ValidationError({'period': _('Start date is required.')})
        if self.period.upper is not None and self.period.upper < self.period.lower + datetime.timedelta(days=1):
            raise ValidationError({'period': _('End date must be at least one day after start date.')})

        if self.country_calendar_code:
            try:
                get_country_holidays(country_calendar_code=self.country_calendar_code)
            except NotImplementedError:
                raise ValidationError(
                    {'country_calendar_code': f'Wrong country_calendar_code {self.country_calendar_code}'}
                )

    def build_day(
        self,
        day: datetime.date | KrmDay,
        task_entries: 'Iterable[TaskEntry | dict] | None' = None,
        reset: bool = False,
        **kwargs,
    ) -> 'DayEntry':
        """Build a day entry using the DayEntryProcessor."""
        return DayEntryProcessor(resource=self.resource, day=day, contract=self).build_day(
            task_entries=task_entries, reset=reset, **kwargs
        )

    def get_tasks(self) -> 'list[Task]':
        """Return all tasks worked during this contract."""
        from krm3.core.models import Task  # noqa: PLC0415

        contract_interval = (
            self.period.lower,
            self.period.upper - datetime.timedelta(days=1) if self.period.upper else DATE_INFINITE,
        )

        ret = []
        for task in Task.objects.filter(resource=self.resource).order_by('start_date'):
            task_interval = (task.start_date, task.end_date or DATE_INFINITE)
            if (contract_interval[0] <= task_interval[0] <= contract_interval[1]) or (
                contract_interval[0] <= task_interval[1] <= contract_interval[1]
            ):
                ret.append(task)
        return ret

    @property
    def document_url(self) -> str | None:
        """Return the authenticated URL for the contract document."""
        if self.document:
            return reverse('media-auth:contract-document', args=[self.pk])
        return None

    def get_remaining_due_hours(self, day: datetime.date, task_id: int | None = None) -> D:
        """Calculate the difference between expected scheduled hours and hours logged thus far."""
        return self.dayentry_set.filter(date=day).remaining_hours

    def fetch(self, resource: 'Resource', day: KrmDay | datetime.date) -> 'Contract':
        """Fetch the contract from the resource and day."""
        return Contract.objects.get(resource=resource, period__in=day.date if isinstance(day, KrmDay) else day)

    # def validate_rule(self, day_entry: 'DayEntry', task_entries: Iterable['TaskEntry'] | None = None) -> None:
    #     due_hours = day_entry.due_hours
    #
    #     # Holiday: equivalent to the expected Due Hours
    #     if day_entry.holiday_hours > 0 and day_entry.holiday_hours != due_hours:
    #         raise ValidationError(
    #             _('Holiday hours must be equal to due hours ({due_hours})').format(due_hours=due_hours),
    #             code='holiday_hours_mismatch',
    #         )
    #
    #     # Sick: equivalent to the expected Due Hours
    #     if day_entry.sick_hours > 0 and day_entry.sick_hours != due_hours:
    #         raise ValidationError(
    #             _('Sick hours must be equal to due hours ({due_hours})').format(due_hours=due_hours),
    #             code='sick_hours_mismatch',
    #         )
    #
    #     # worked hours: Day shift + Night shift + Travel
    #     if task_entries is None:
    #         task_entries = day_entry.taskentry_set.all()
    #     worked_hours = sum(te.total_task_hours for te in task_entries)
    #
    #     # Regular hours: up to maximum the expected number of hours (Due Hours)
    #     expected_regular_hours = min(worked_hours, due_hours)
    #     if day_entry.regular_hours != expected_regular_hours:
    #         raise ValidationError(
    #             _('Regular hours mismatch: expected {expected}, got {actual}').format(
    #                 expected=expected_regular_hours, actual=day_entry.regular_hours
    #             ),
    #             code='regular_hours_mismatch',
    #         )
    #
    #     # Overtime: Day shift + Night shift + Travel - Due Hours (min 0)
    #     expected_overtime = max(D(0), worked_hours - due_hours)
    #     if day_entry.overtime_hours != expected_overtime:
    #         raise ValidationError(
    #             _('Overtime hours mismatch: expected {expected}, got {actual}').format(
    #                 expected=expected_overtime, actual=day_entry.overtime_hours
    #             ),
    #             code='overtime_hours_mismatch',
    #         )
    #
    #     # Remaining hours: Due Hours - worked_hours (min 0)
    #     expected_remaining_hours = max(D(0), due_hours - worked_hours)
    #     if day_entry.remaining_hours != expected_remaining_hours:
    #         raise ValidationError(
    #             _('Remaining hours mismatch: expected {expected}, got {actual}').format(
    #                 expected=expected_remaining_hours, actual=day_entry.remaining_hours
    #             ),
    #             code='remaining_hours_mismatch',
    #         )
    #
    #     # Meal Voucher: the meal voucher threshold
    #     meal_threshold = self.meal_threshold(day_entry.day)
    #     if meal_threshold is not None:
    #         expected_meal_voucher = 1 if worked_hours >= meal_threshold else 0
    #         if day_entry.meal_voucher != expected_meal_voucher:
    #             raise ValidationError(
    #                 _('Meal voucher mismatch: expected {expected}, got {actual}').format(
    #                     expected=expected_meal_voucher, actual=day_entry.meal_voucher
    #                 ),
    #                 code='meal_voucher_mismatch',
    #             )

    @cached_property
    def work_schedule(self) -> dict[str, D]:
        """Return the working schedule for the contract cached in the instance."""
        if self.working_schedule:
            return self.working_schedule
        return json.loads(config.DEFAULT_RESOURCE_SCHEDULE)

    @cached_property
    def calendar_code(self) -> str:
        """Return the country calendar code for the contract or the default calendar code if not set."""
        return self.country_calendar_code if self.country_calendar_code else settings.HOLIDAYS_CALENDAR

    @cachedmethod(cache=lambda self: self.__dict__.setdefault('_is_holiday_cache', {}))
    def is_holiday(self, day: datetime.date | KrmDay) -> bool:
        krmday = KrmDay(day)
        return krmday.is_holiday(self.calendar_code, include_sundays_as_holiday=self.sunday_as_holiday)

    @cachedmethod(cache=lambda self: self.__dict__.setdefault('_meal_threshold_cache', {}))
    def meal_threshold(self, day: datetime.date | KrmDay) -> D | None:
        """Return the meal threshold for the day."""
        if not self.meal_voucher:
            return None
        krmday = KrmDay(day)
        return D(self.meal_voucher[krmday.day_of_week_short.casefold()])

    def is_working_day(self, day: datetime.date | KrmDay) -> bool:
        """Return True if the given day is a working day."""
        return not self.is_holiday(day) and self.work_schedule[KrmDay(day).day_of_week_short.casefold()] > 0

    def period_as_tuple(self) -> tuple:
        """Return a tuple of the period as a tuple.

        If upper bound is None then Maxdate is used instead.
        """
        return self.period.lower, self.period.upper if self.period.upper is not None else datetime.date.max

    def get_due_hours(self, day: datetime.date | KrmDay) -> D:
        """Return the due hours for the given day."""
        day = KrmDay(day)
        if not self.falls_in(day):
            raise RuntimeError(_('Unable to get due hours: date outside contract period'))
        if self.is_holiday(day):
            return D(0)
        return D(self.work_schedule[day.day_of_week_short.casefold()])

    def falls_in(self, day: datetime.date | KrmDay) -> bool:
        """Check if the provided day falls into the contract period."""
        day = KrmDay(day)
        lower, upper = self.period_as_tuple()
        return lower <= day < upper
