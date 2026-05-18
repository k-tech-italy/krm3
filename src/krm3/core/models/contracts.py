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
from ktcalendars import KTDay
from ktcalendars.ranges import KTDateRange
from ktcalendars.utils import get_country_holidays

from krm3.config import settings
from krm3.core.storage import PrivateMediaStorage
from krm3.missions.media import contract_directory_path
from krm3.timesheet.operations import DayEntryProcessor

if TYPE_CHECKING:
    from krm3.core.models import Contract, DayEntry, Resource, TaskEntry
    from krm3.core.models.auth import User


class ContractQuerySet(models.QuerySet['Contract']):
    def active_between(self, start: datetime.date, end: datetime.date) -> Self:
        """Return the contracts valid in the given interval.

        :param start: the start of the interval (inclusive).
        :param end: the end of the interval (inclusive).
        :return: the filtered `Contract`s.
        """
        return self.filter(period__overlap=KTDateRange.from_start_end(start, end))

    def filter_acl(self, user: 'User') -> Self:
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.has_any_perm('core.view_any_contract', 'core.manage_any_contract'):
            return self.all()
        return self.filter(resource__user=user)

    def by_day(self, resource: 'Resource', day: datetime.date | KTDay) -> 'Contract | None':
        """Return contract for the given resource and day."""
        return self.filter(resource=resource, period__contains=KTDay(day).date).first()


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
        day: datetime.date | KTDay,
        task_entries: 'Iterable[TaskEntry | dict] | None' = None,
        reset: bool = False,
        **kwargs,
    ) -> 'DayEntry':
        """Build a day entry using the DayEntryProcessor."""
        return DayEntryProcessor(resource=self.resource, day=day, contract=self).build_day(
            task_entries=task_entries, reset=reset, **kwargs
        )

    @property
    def document_url(self) -> str | None:
        """Return the authenticated URL for the contract document."""
        if self.document:
            return reverse('media-auth:contract-document', args=[self.pk])
        return None

    def get_remaining_due_hours(self, day: datetime.date, task_id: int | None = None) -> D:
        """Calculate the difference between expected scheduled hours and hours logged thus far."""
        return self.dayentry_set.filter(date=day).remaining_hours

    def fetch(self, resource: 'Resource', day: KTDay | datetime.date) -> 'Contract':
        """Fetch the contract from the resource and day."""
        return Contract.objects.get(resource=resource, period__in=day.date if isinstance(day, KTDay) else day)

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

    @cachedmethod(cache=lambda self: self.__dict__.setdefault('_meal_threshold_cache', {}))
    def meal_threshold(self, day: datetime.date | KTDay) -> D | None:
        """Return the meal threshold for the day."""
        if not self.meal_voucher:
            return None
        ktday = KTDay(day)
        return D(self.meal_voucher[ktday.day_of_week_short.casefold()])

    def get_due_hours(self, day: datetime.date | KTDay) -> D:
        """Return the due hours for the given day."""
        day = self.get_ktday(day)
        if day.is_holiday:
            return D(0)
        return D(self.work_schedule[day.day_of_week_short.casefold()])

    def get_ktday(self, day: datetime.date | KTDay, silent: bool = False) -> KTDay | None:
        """Normalise the provided date in a KTDay with the Contract calendar.

        If the date falls outside the contract period, return None or raise a ValueError if silent is False.
        """
        day = KTDay(day, cal_country_code=self.calendar_code)
        result = day in self.period
        if not result and not silent:
            raise ValueError(_('Date outside contract period'))
        return day if result else None
