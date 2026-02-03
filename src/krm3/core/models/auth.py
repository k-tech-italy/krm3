from __future__ import annotations

import datetime
import json
from decimal import Decimal
from typing import Any, Self, TYPE_CHECKING

from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django.db.models import Sum
from natural_keys import NaturalKeyModel
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
import vobject

from krm3.config import settings
from krm3.utils.dates import KrmCalendar, KrmDay
from constance import config

if TYPE_CHECKING:
    from datetime import date
    from krm3.core.models import Contract


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **kwargs: Any) -> User:
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **kwargs)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username: str, email: str, password: str | None = None, **kwargs: Any) -> User:
        kwargs.setdefault('is_active', True)
        kwargs.setdefault('is_staff', True)
        kwargs.setdefault('is_superuser', True)
        if kwargs.get('is_active') is not True:
            raise ValueError('Superuser must be active')
        if kwargs.get('is_staff') is not True:
            raise ValueError('Superuser must be staff')
        if kwargs.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        return self.create_user(email, password, username=username, **kwargs)


class User(AbstractUser):
    objects = UserManager()  # type: ignore
    picture = models.TextField(null=True, blank=True)
    social_profile = models.TextField(null=True, blank=True)

    if TYPE_CHECKING:
        profile: 'UserProfile'

    @staticmethod
    def get_natural_key_fields() -> list[str]:
        return ['username']

    def get_resource(self) -> 'Resource':
        """Return the associated resource or None if not available."""
        try:
            resource = self.resource
        except self.__class__.resource.RelatedObjectDoesNotExist:
            resource = None
        return resource

    def can_manage_or_view_any_project(self) -> bool:
        """Check if user has RO/RW permissions for any project.

        :return: `True` if the user is allowed to view or edit data on projects for any resource,
           `False` otherwise.
        """
        return self.has_any_perm('core.manage_any_project', 'core.view_any_project')

    def has_any_perm(self, *perms: str) -> bool:
        """Check that the user has at least one of the given permissions.

        :param : the permissions to check
        :return: `True` if the user has at least one of the given
          `perms`, `False` otherwise.
        """
        return any(self.has_perm(perm) for perm in perms)


class UserProfile(NaturalKeyModel):
    """The Profile is used to record the user profile picture in social auth."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    picture = models.TextField(null=True, blank=True)
    social_profile = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.user.username

    @classmethod
    def new(cls, user: User) -> Self:
        return cls.objects.create(user=user)


class Resource(models.Model):
    """A person, e.g. an employee or external contractor."""

    profile = models.OneToOneField(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    preferred_in_report = models.BooleanField(default=True)
    vcard_text = models.TextField(null=True, blank=True)
    fiscal_code = models.CharField(max_length=25, null=True, blank=True, unique=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self) -> str:
        return f'{self.first_name} {self.last_name}'

    def clean(self) -> None:
        """Validate the model fields."""
        super().clean()
        self._validate_vcard_text()

    @property
    def full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'

    def _validate_vcard_text(self) -> None:
        """Validate that vcard_text contains a valid vCard format.

        Empty values (None or empty string) are allowed and no validation is applied.
        Non-empty values must be parseable as vCard using vobject library.
        Supports vCard 2.1, 3.0, and 4.0 formats, including Apple-specific extensions.
        """
        # Allow None or empty string - no validation applied
        if self.vcard_text:
            self.vcard_text = '\n'.join([x.strip() for x in self.vcard_text.splitlines()])

        if not self.vcard_text:
            return

        try:
            # Try to parse the vCard text
            vobject.readOne(self.vcard_text)
        except vobject.base.ParseError as e:
            # ParseError is raised for malformed vCards
            raise ValidationError({'vcard_text': f'Invalid vCard format: {str(e)}'}) from e
        except Exception as e:
            # Catch any other unexpected errors
            raise ValidationError({'vcard_text': f'Error parsing vCard: {str(e)}'}) from e

    def scheduled_working_hours_for_day(self, day: KrmDay) -> float:
        """Scheduled number of hours a resource should work each day.

        :return: scheduled number of hours.
        """
        from krm3.core.models import Contract  # noqa: PLC0415

        contract = Contract.objects.filter(resource=self, period__contains=day.date).first()
        return self._get_min_working_hours(contract, day)

    def _get_min_working_hours(self, contract: Contract | None, day: KrmDay) -> float:
        """Return the minimum working hours for a given day."""
        if contract and contract.work_schedule:
            min_working_hours = contract.work_schedule.get_hours_for_day(day.date)
        else:
            schedule = json.loads(config.DEFAULT_RESOURCE_SCHEDULE)
            # FIXME: this could also be a list...
            min_working_hours = schedule[day.day_of_week_short.lower()]
        if contract and contract.country_calendar_code:
            country_calendar_code = contract.country_calendar_code
        else:
            country_calendar_code = settings.HOLIDAYS_CALENDAR

        if day.is_holiday(country_calendar_code, False):
            min_working_hours = 0
        return min_working_hours

    def get_krm_days_with_contract(self, start_day: date, end_day: date) -> list[KrmDay]:
        """Return a list of Krm days tailored for the resource contract/schedule.

        Attributes added to KRM Day:
        - contract: The contract for the day if available
        - min_working_hours: the minimum working hours for the day (Result is based on resource calendar and schedule)
        - is_holiday (overridden method. Result is contract country calendar aware)
        """
        days_list = list(KrmCalendar().iter_dates(start_day, end_day))
        contracts = self.get_contracts(start_day, end_day)

        for kd in days_list:
            kd.contract = None
            kd.min_working_hours = 0

            country_calendar_code = settings.HOLIDAYS_CALENDAR
            for contract in contracts:
                if contract.falls_in(kd.date):
                    kd.contract = contract
                    kd.min_working_hours = self._get_min_working_hours(contract, kd)
                    if contract.country_calendar_code:
                        country_calendar_code = contract.country_calendar_code
                    break

            if kd.is_holiday(country_calendar_code, True):
                kd.is_holiday = lambda *args, **kwargs: True
            else:
                kd.is_holiday = lambda *args, **kwargs: False

        return days_list

    def get_contracts(self, start_day: date, end_day: date) -> list[Contract]:
        """Return a list of contracts applicable to the time interval between start_day and end_day."""
        from krm3.core.models import Contract  # noqa: PLC0415

        return list(
            Contract.objects.filter(
                period__overlap=(start_day, end_day + datetime.timedelta(days=1) if end_day else None), resource=self
            )
        )

    def contract_for_date(self, contract_list: 'list[Contract]', day: date | KrmDay) -> 'Contract | None':
        """Select the contract applicable for the given day."""
        for contract in contract_list:
            if contract.falls_in(day):
                return contract
        return None

    def get_schedule(self, start_day: date, end_day: date) -> dict[date, float]:
        calendar = KrmCalendar()
        days = list(calendar.iter_dates(start_day, end_day))

        for day in days:
            day.min_working_hours = self.scheduled_working_hours_for_day(day)

        return {day.date: day.min_working_hours for day in days}

    def get_bank_hours_balance(self) -> Decimal:
        """Calculate bank hours balance from all time entries."""
        from krm3.core.models import TimeEntry  # noqa: PLC0415

        queryset = TimeEntry.objects.filter(resource=self)
        result = queryset.aggregate(total_deposits=Sum('bank_to'), total_withdrawals=Sum('bank_from'))

        deposits = result['total_deposits'] or Decimal(0)
        withdrawals = result['total_withdrawals'] or Decimal(0)

        return deposits - withdrawals


@receiver(post_save, sender=User)
def create_user_profile(sender: User, instance: User, created: bool, **kwargs: dict) -> None:
    if created:
        UserProfile.new(user=instance)
