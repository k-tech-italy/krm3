from __future__ import annotations

import datetime
from decimal import Decimal
import json
from typing import Self, override

import constance
from django.contrib.postgres import constraints as pg_constraints
from django.contrib.postgres import fields as pg_fields
from django.core.exceptions import ValidationError
from django.db import models

from krm3.core.models.contracts import Contract
from krm3.utils.dates import KrmDay


def _get_full_default_schedule() -> list[Decimal]:
    schedule = json.loads(constance.config.DEFAULT_RESOURCE_SCHEDULE)
    if isinstance(schedule, dict):
        try:
            return [Decimal(schedule[day]) for day in ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')]
        except KeyError as e:
            raise TypeError(
                'Default schedule as a dict should have lowercase abbreviated day of week names as keys - '
                f'this schedule is missing key "{e}"'
            ) from e
    if isinstance(schedule, list) and len(schedule) == 7:
        try:
            return [Decimal(item) for item in schedule]
        except ArithmeticError as e:
            raise TypeError(
                'Default schedule as a list should only contain numbers - '
                f'got an error while converting items to decimal: {e}'
            )
    raise TypeError('Default schedule must be either a dict or a 7 numbers long list')


def _default_schedule() -> list[Decimal]:
    schedule = _get_full_default_schedule()
    return list(map(Decimal, schedule))


class ScheduleQuerySet[T: Schedule](models.QuerySet[T]):
    def valid_on(self, day: datetime.date) -> Self:
        return self.filter(period__contains=day)


class Schedule(models.Model):
    """Represents a weekly schedule in hours."""

    period = pg_fields.DateRangeField()
    hours = pg_fields.ArrayField(
        models.DecimalField(max_digits=4, decimal_places=2),
        size=7,
        default=_default_schedule,
        # TODO: i18n
        help_text=(
            'An array of 7 numbers, one for each day of the week, representing scheduled hours for that day. '
            "First element is Monday's schedule, second is Tuesday's, ..., last is Sunday's."
        ),
    )
    """A 7-items sequence containing hours for each day of the week.

    Indices correspond to the return value of `datetime.date.weekday()`.
    Monday: 0, ... Sunday: 6.
    """

    objects = ScheduleQuerySet.as_manager()

    class Meta:
        abstract = True

    def __str__(self) -> str:
        start_date_part = f'from {self.period.lower}'
        end_date_part = f' to {self.period.upper} (excluded)' if self.period.upper else ''
        hours = tuple(str(day_hours for day_hours in self.hours))
        return f'{self._describe()} {start_date_part}{end_date_part}: {hours}'

    @override
    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)

    @override
    def clean(self) -> None:
        super().clean()

        if any(h < 0 and h > 24 for h in self.hours):
            # TODO: i18n
            raise ValidationError({'hours': 'All hours must be between 0 and 24.'})

    @classmethod
    def new(cls, start: datetime.date, end: datetime.date | None = None, **kwargs) -> Self:
        return cls.objects.create(period=(start, end), **kwargs)

    def get_hours_for_day(self, day: datetime.date) -> Decimal:
        return self.hours[day.weekday()]

    def get_hours_for_today(self) -> Decimal:
        return self.get_hours_for_day(datetime.date.today())

    def _describe(self) -> str:
        return 'Schedule'


class WorkSchedule(Schedule):
    # FIXME: should be one-to-one
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='work_schedules')

    class Meta(Schedule.Meta):
        constraints = (
            pg_constraints.ExclusionConstraint(
                name='exclude_overlapping_work_schedules_for_contract',
                expressions=[
                    ('period', pg_fields.RangeOperators.OVERLAPS),
                    ('contract', pg_fields.RangeOperators.EQUAL),
                ],
            ),
        )

    @override
    def _describe(self) -> str:
        return f"{self.contract.resource}'s work schedule"


class MealVoucherThresholds(Schedule):
    # FIXME: national_holiday_hours?
    non_working_day_hours = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal(4.0))
    """The meal voucher threshold for any non-working day (e.g. national holidays)"""

    # FIXME: should be one-to-one
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='meal_voucher_thresholds')

    class Meta(Schedule.Meta):
        constraints = (
            pg_constraints.ExclusionConstraint(
                name='exclude_overlapping_meal_voucher_thresholds_for_contract',
                expressions=[
                    ('period', pg_fields.RangeOperators.OVERLAPS),
                    ('contract', pg_fields.RangeOperators.EQUAL),
                ],
            ),
        )

    @override
    def __str__(self) -> str:
        return super().__str__() + f' ({self.non_working_day_hours} for non-working days)'

    @override
    def _describe(self) -> str:
        return f"{self.contract.resource}'s meal voucher threshold"

    @override
    def get_hours_for_day(self, day: datetime.date) -> Decimal:
        if KrmDay(day).is_holiday(
            country_calendar_code=self.contract.country_calendar_code, include_sundays_as_holiday=False
        ):
            return self.non_working_day_hours
        return super().get_hours_for_day(day)
