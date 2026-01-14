from __future__ import annotations

import datetime
from typing import Self, TYPE_CHECKING

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from krm3.missions.media import contract_directory_path
from krm3.utils.dates import DATE_INFINITE, KrmDay, get_country_holidays

if TYPE_CHECKING:
    from decimal import Decimal

    from django.db.models.fields.related_descriptors import RelatedManager
    from krm3.core.models import Task
    from krm3.core.models import schedule


class ContractQuerySet(models.QuerySet['Contract']):
    def active_between(self, start: datetime.date, end: datetime.date) -> Self:
        """Return the contracts valid in the given interval.

        :param start: the start of the interval (inclusive).
        :param end: the end of the interval (inclusive).
        :return: the filtered `Contract`s.
        """
        end = end + datetime.timedelta(days=1)
        return self.filter(period__overlap=(start, end))


class Contract(models.Model):
    resource = models.ForeignKey('core.Resource', on_delete=models.CASCADE)
    period = DateRangeField(help_text='NB: End date is the day after the actual end date')
    country_calendar_code = models.CharField(
        null=True,
        blank=True,
        help_text='Country calendar code as per https://holidays.readthedocs.io/en/latest/#available-countries',
    )
    comment = models.TextField(null=True, blank=True, help_text='Optional comment about the contract')
    document = models.FileField(
        upload_to=contract_directory_path,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf'])],
        help_text='Optional PDF document (PDF files only)',
    )

    objects = ContractQuerySet.as_manager()

    if TYPE_CHECKING:
        work_schedules: RelatedManager[schedule.WorkSchedule]
        meal_voucher_thresholds: RelatedManager[schedule.MealVoucherThresholds]

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

    def __str__(self) -> str:
        if self.period.lower is None:
            return 'Invalid Contract (No start date)'
        if self.period.upper:
            end_dt = self.period.upper - datetime.timedelta(days=1)
            return f'{self.period.lower.strftime("%Y-%m-%d")} - {end_dt.strftime("%Y-%m-%d")}'
        return f'{self.period.lower.strftime("%Y-%m-%d")} - ...'

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()

        if self.period.lower is None:
            raise ValidationError({'period': 'Start date is required.'})
        if self.period.upper is not None and self.period.upper < self.period.lower + datetime.timedelta(days=1):
            raise ValidationError({'period': 'End date must be at least one day after start date.'})

        if self.country_calendar_code:
            try:
                get_country_holidays(country_calendar_code=self.country_calendar_code)
            except NotImplementedError:
                raise ValidationError(
                    {'country_calendar_code': f'Wrong country_calendar_code {self.country_calendar_code}'}
                )

    def falls_in(self, day: datetime.date | KrmDay) -> bool:
        """Check if the provided day falls into the contract period."""
        if isinstance(day, KrmDay):
            day = day.date
        if self.period.upper is None:
            return self.period.lower <= day
        return self.period.lower <= day < self.period.upper

    def get_tasks(self) -> list['Task']:
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

    def get_due_hours(self, day: datetime.date | KrmDay) -> Decimal:
        day = KrmDay(day)
        if not self.falls_in(day):
            from krm3.utils import schedule as schedule_utils  # noqa: PLC0415 - circular import

            return schedule_utils.get_default_schedule(self, day.date)
        return self.get_scheduled_hours_for_day(day.date)

    def working_schedule(self, day: datetime.date | None) -> schedule.WorkSchedule:
        """Return the weekly work schedule for the given `day`.

        :param day: the day for which the schedule is valid.
            Defaults to today.
        :return: a weekly schedule.
        """
        if not day:
            day = datetime.date.today()
        return self.work_schedules.valid_on(day).get()

    def get_scheduled_hours_for_day(self, day: datetime.date) -> Decimal:
        """Return how long the contract's resource is supposed work on a given `day`.

        :param day: the day to check the schedule for
        :return: how many hours the resource is supposed to work on the
            given `day`.
        """
        return self.working_schedule(day).get_hours_for_day(day)

    def meal_voucher(self, day: datetime.date | None) -> schedule.MealVoucherThresholds | None:
        """Return the weekly meal voucher thresholds for the given `day`.

        :param day: the day for which the thresholds are valid.
            Defaults to today.
        :return: a weekly schedule.
        """
        if not day:
            day = datetime.date.today()
        return self.meal_voucher_thresholds.valid_on(day).first()
