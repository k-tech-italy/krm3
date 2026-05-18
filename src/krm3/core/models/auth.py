from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Self

import vobject
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from ktcalendars import KTDateRange, KTDay
from natural_keys import NaturalKeyModel
from psycopg.types.range import DateRange

from krm3.config import settings
from krm3.utils.db.postgresql.funcs import DateRangeIntersection
from krm3.utils.numbers import safe_dec

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal as D  # noqa: N817

    from ktcalendars.types import KTDayType

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


class ResourceQuerySet(models.QuerySet['Resource']):
    def active_between(self, start: datetime.date, end: datetime.date | None = None) -> Self:
        """Return the contracts valid in the given interval.

        :param start: the start of the interval (inclusive).
        :param end: the end of the interval (inclusive).
        :return: the filtered `Contract`s.
        """
        if isinstance(start, DateRange):
            period = start
        else:
            period = KTDateRange.from_start_end(start, end)
        return self.filter(contract__period__overlap=period).distinct()


class Resource(models.Model):
    """A person, e.g. an employee or external contractor."""

    profile = models.OneToOneField(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    preferred_in_report = models.BooleanField(default=True)
    vcard_text = models.TextField(null=True, blank=True)
    fiscal_code = models.CharField(max_length=25, null=True, blank=True, unique=True)
    preferred_language = models.CharField(choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)

    objects = ResourceQuerySet.as_manager()

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

    def scheduled_working_hours_for_day(self, day: KTDay) -> float:
        """Scheduled number of hours a resource should work each day.

        :return: scheduled number of hours.
        """
        from krm3.core.models import Contract  # noqa: PLC0415

        contract = Contract.objects.filter(resource=self, period__contains=day.date).first()
        return contract.get_due_hours(day)

    def get_contract_map(self, start_day: date, end_day: date, with_blanks: bool = True) -> dict[KTDateRange, Contract]:
        """Return a dict of {KTDateRange(period): contracts} applicable to the time interval.

        The period in the KrmDateRange(period) is the actual intersection of the contract's period with the requested
        date range.

        If with_blanks is True, the gap periods are filled with `period: None`.
        """
        from krm3.core.models import Contract  # noqa: PLC0415

        # NB: end date workaround may change with fixed versions of ktcalendars
        search_range = KTDateRange.from_start_end(start_day, end_day if end_day != datetime.date.max else None)
        contracts = (
            Contract.objects.filter(period__overlap=search_range, resource=self)
            .annotate(intersection=DateRangeIntersection(F('period'), search_range))
            .order_by('period')
        )
        contracts = {KTDateRange(c.intersection): c for c in contracts}

        if with_blanks:
            gaps = KTDateRange.gaps(contracts.keys(), start_day, end_day)
            contracts.update(dict.fromkeys(gaps, None))
        return contracts

    def has_contract_cover(self, start_day: date, end_day: date, partial: bool = False, atomic: bool = False) -> bool:
        """Return True if there is contract coverage for the given date range.

        If partial is False then the whole period must be covered by contracts.
        If atomic is True then one and only one Contract must cover the period.
        """
        contracts = sorted(self.get_contract_map(start_day, end_day, with_blanks=False).keys())
        if len(contracts) == 0:
            return False
        if partial is False and len(KTDateRange.gaps(contracts, start_day, end_day)) > 0:
            return False
        if atomic and len(contracts) >= 1:
            return False
        if partial:
            return True
        return (contracts[0].as_dates()[0], contracts[-1].as_dates()[1]) == (start_day, end_day or datetime.date.max)

    def get_schedule(self, start_day: date, end_day: date) -> dict[date, float]:
        contracts = self.get_contract_map(start_day, end_day, with_blanks=True)

        result = {}
        for period, contract in contracts.items():
            for day in period:
                if contract is None:
                    result[day] = 0.0
                else:
                    result[day] = contract.get_due_hours(day)
        return result

    # TODO: this method will last longer and longer. Fix it
    def get_bank_hours_balance(self, at: KTDayType) -> D:
        """Calculate bank hours balance from all time entries."""
        from krm3.core.models import DayEntry  # noqa: PLC0415

        at = KTDay(at).date
        bank = DayEntry.objects.filter(resource=self, day__lte=at).aggregate(total_bank=Sum('bank'))

        return safe_dec(bank['total_bank'])


@receiver(post_save, sender=User)
def create_user_profile(sender: User, instance: User, created: bool, **kwargs: dict) -> None:
    if created:
        UserProfile.new(user=instance)
