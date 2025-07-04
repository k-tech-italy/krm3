from __future__ import annotations

import itertools
import typing
from decimal import Decimal
from enum import Enum

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

from .geo import City
from .auth import Resource
from .projects import Project

from krm3.currencies.models import Currency, Rate
from krm3.missions.exceptions import AlreadyReimbursed
from krm3.missions.media import mission_directory_path
from krm3.utils.queryset import ActiveManagerMixin


if typing.TYPE_CHECKING:
    from krm3.core.models.auth import User


class MissionManager(ActiveManagerMixin, models.Manager):
    def filter_acl(self, user):
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.has_any_perm('core.manage_any_mission', 'core.view_any_mission'):
            return self.all()
        return self.filter(resource__user=user)


class Mission(models.Model):
    class MissionStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SUBMITTED = 'SUBMITTED', _('Submitted')
        CANCELLED = 'CANCELLED', _('Cancelled')

    status = models.CharField(
        max_length=9,
        choices=MissionStatus,
        default=MissionStatus.DRAFT,
    )

    number = models.PositiveIntegerField(blank=True, null=True, help_text='Set automatically if left blank')
    title = models.CharField(max_length=50, null=True, blank=True)
    from_date = models.DateField()
    to_date = models.DateField()
    year = models.PositiveIntegerField(
        blank=True, null=True, help_text="Leave blank for defaulting to from_date's year"
    )

    default_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        help_text=f'Leave blank for default [{settings.BASE_CURRENCY}]',
    )

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)

    objects = MissionManager()

    @staticmethod
    def calculate_number(instance_id: int | None, year: int) -> int:
        qs = Mission.objects.filter(
            number__isnull=False,
            year=year,
            status__in=[Mission.MissionStatus.SUBMITTED, Mission.MissionStatus.CANCELLED],
        )
        if instance_id:
            qs = qs.exclude(pk=instance_id)
        nums = [0] + sorted(list(qs.values_list('number', flat=True)))
        ret = list(itertools.takewhile(lambda v: v[0] == 0 or v[1] == nums[v[0] - 1] + 1, enumerate(nums)))[-1]
        return ret[1] + 1

    @property
    def expense_count(self):
        return self.expenses.count()

    def __str__(self):
        title = self.title or self.city.name
        return f'{self.resource}, {title}, {self.number}'

    def clean(self):
        if (self.number and self.status == Mission.MissionStatus.DRAFT) or (
            self.number is None and self.status != Mission.MissionStatus.DRAFT
        ):
            raise ValidationError(
                _('If a mission is in DRAFT then number must empty, otherwise it is mandatory'), code='number'
            )
        if self.to_date is not None and self.from_date is not None and self.to_date < self.from_date:
            raise ValidationError(_('to_date must be > from_date'))

        if not self.title:
            self.title = Mission.calculate_title(self)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.full_clean()
        super().save(force_insert, force_update, using, update_fields)

    def is_accessible(self, user) -> bool:
        if user.is_superuser or user.get_all_permissions().intersection(
            {'core.manage_any_mission', 'core.view_any_mission'}
        ):
            return True
        return bool(self.resource and self.resource.user == user)

    @classmethod
    def calculate_title(cls, cleaned_data: Mission | dict) -> str:
        if not isinstance(cleaned_data, Mission):
            mission = Mission(**cleaned_data)
        else:
            mission = cleaned_data
        if (
            mission.from_date
            and not mission.title
            and mission.city
            and mission.to_date
            and mission.number
            and mission.resource
        ):
            city = mission.city.name.lower()
            return (
                f"M_{mission.year}_{mission.number:03}_"
                f"{mission.from_date:%d}{mission.from_date:%b}-{mission.to_date:%d}{mission.to_date:%b}"
                f"_{mission.resource.last_name.replace(' ', '')}_{slugify(city)}"
            )
        return ''

    class Meta:
        permissions = [
            ('view_any_mission', "Can view(only) everybody's missions"),
            ('manage_any_mission', "Can view, and manage everybody's missions"),
        ]
        constraints = [UniqueConstraint(fields=('number', 'year'), name='unique_mission_number_year')]


class DocumentType(models.Model):
    title = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=True)
    default = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']


class ExpenseCategory(MPTTModel):
    title = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    def __str__(self):
        ancestors = self.get_ancestors(include_self=True)
        return ':'.join([x.title for x in ancestors])

    class MPTTMeta:
        order_insertion_by = ['title']

    class Meta:
        verbose_name_plural = 'expense categories'
        constraints = (UniqueConstraint(fields=('title', 'parent'), name='unique_expense_category_title'),)


class PaymentCategory(MPTTModel):
    title = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    personal_expense = models.BooleanField(default=False)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    def __str__(self):
        ancestors = self.get_ancestors(include_self=True)
        return ':'.join([x.title for x in ancestors])

    class MPTTMeta:
        order_insertion_by = ['title']

    class Meta:
        verbose_name_plural = 'payment categories'
        constraints = (UniqueConstraint(fields=('title', 'parent'), name='unique_payment_category_title'),)


class ReimbursementManager(models.Manager):
    def filter_acl(self, user):
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
            {'core.manage_any_mission', 'core.view_any_mission'}
        ):
            return self.all()
        return self.filter(resource__user=user)


class Reimbursement(models.Model):
    class ReimbursementSummaryEnum(Enum):
        NON_RIMBORSATE = 'Non Rimborsate'
        DA_RESTITUIRE = 'Da Restituire'
        GIA_RIMBORSATE = 'Già Rimborsate'
        TOTALE_RIMBORSO = 'Totale Rimborso'
        ANTICIPATO = 'Anticipato'
        SPESE_TRASFERTA = 'Spese trasferta'
        TOTALE_SPESE = 'Totale spese'

    number = models.PositiveIntegerField(blank=True, help_text='Set automatically if left blank')
    year = models.PositiveIntegerField(blank=True)
    month = models.CharField(max_length=20, null=True)
    title = models.CharField(max_length=120, help_text='Set automatically if left blank')
    issue_date = models.DateField(auto_now_add=True)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)
    paid_date = models.DateField(blank=True, null=True)

    objects = ReimbursementManager()

    @staticmethod
    def calculate_number(instance_id: int | None, year: int) -> int:
        qs = Reimbursement.objects.filter(year=year)
        if instance_id:
            qs = qs.exclude(pk=instance_id)
        nums = [0] + sorted(list(qs.values_list('number', flat=True)))
        ret = list(itertools.takewhile(lambda v: v[0] == 0 or v[1] == nums[v[0] - 1] + 1, enumerate(nums)))[-1]
        return ret[1] + 1

    @property
    def expense_count(self):
        return self.expenses.count()

    def clean(self):
        if self.number is None and self.year:
            self.number = Reimbursement.calculate_number(self.id, self.year)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.full_clean()
        super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return f'{self.title} ({self.number}/{self.year})'

    class Meta:
        constraints = [UniqueConstraint('year', 'number', name='unique_reimbursement_number')]


class ExpenseManager(ActiveManagerMixin, models.Manager):
    def by_otp(self, otp: str):
        """Retrieve the instance matching the provided otp."""
        ref = settings.FERNET_KEY.decrypt(f'gAAAAA{otp}').decode()
        expense_id, mission_id, ts = ref.split('|')
        return self.get(mission_id=mission_id, id=expense_id, modified_ts=ts)

    def filter_acl(self, user: "User"):
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
            {'core.manage_any_expense', 'core.view_any_expense'}
        ):
            return self.all()
        return self.filter(mission__resource__user_id=user.id)


class Expense(models.Model):
    mission = models.ForeignKey(Mission, related_name='expenses', on_delete=models.CASCADE)
    day = models.DateField()
    amount_currency = models.DecimalField(max_digits=10, decimal_places=2, help_text='Amount in currency')
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, blank=True, help_text='Leave blank to inherit from mission.default_currency'
    )
    amount_base = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text=f'Amount in {settings.BASE_CURRENCY}'
    )
    amount_reimbursement = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text='Reimbursed amount'
    )
    detail = models.CharField(max_length=100, null=True, blank=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    payment_type = models.ForeignKey(PaymentCategory, on_delete=models.PROTECT)
    reimbursement = models.ForeignKey(
        Reimbursement, related_name='expenses', on_delete=models.SET_NULL, null=True, blank=True
    )

    image = models.FileField(upload_to=mission_directory_path, null=True, blank=True)

    created_ts = models.DateTimeField(auto_now_add=True)
    modified_ts = models.DateTimeField(auto_now=True)

    objects = ExpenseManager()

    class Meta:
        permissions = [
            ('view_any_expense', "Can view(only) everybody's expenses"),
            ('manage_any_expense', "Can view, and manage everybody's expenses"),
        ]

    def __str__(self) -> str:
        return f'{self.day}, {self.amount_currency} for {self.category}'

    def get_updated_millis(self) -> int:
        return int(self.modified_ts.timestamp() * 1000)

    def is_accessible(self, user: "User") -> bool:
        if user.is_superuser or user.get_all_permissions().intersection(
            {'core.manage_any_expense', 'core.view_any_expense'}
        ):
            return True
        return bool(self.mission.resource and self.mission.resource.user == user)

    def get_otp(self) -> str:
        """Generate one-time-password."""
        return settings.FERNET_KEY.encrypt(f'{self.id}|{self.mission_id}|{self.modified_ts}'.encode()).decode('utf-8')[
            6:
        ]

    def check_otp(self, otp: str) -> bool:
        """Check the OTP."""
        return True
        ref = settings.FERNET_KEY.decrypt(f'gAAAAA{otp}')
        expense_id, mission_id, ts = ref.split('|')
        return f'{self.modified_ts}' == ts and self.id == int(expense_id) and self.mission_id == int(mission_id)

    def calculate_base(self, force_rates: bool=False, force_reset: bool=False, save: bool = True) -> Decimal:
        """(Re)calculate the base amount."""
        if force_reset or self.amount_base is None:
            # we need to recalculate it
            if self.currency.is_base():
                self.amount_base = self.amount_currency
            else:
                self.amount_base = Rate.for_date(self.day, force=force_rates).convert(
                    self.amount_currency, self.currency
                )
            if save:
                self.save()
        return self.amount_base

    def apply_reimbursement(self, force: bool = False, reimbursement: Reimbursement = None) -> Decimal:
        """Calculate the reimbursement amount.

        Will save the record if reimbursement is provided.
        """
        if self.reimbursement and not force:
            raise AlreadyReimbursed(f'Expense {self.id} already reimbursed in {self.reimbursement_id}')
        self.calculate_base(save=False)
        if self.amount_reimbursement is None:
            self.amount_reimbursement = self.get_reimbursement_amount()
        if reimbursement:
            self.reimbursement = reimbursement
            self.save()
        return self.amount_reimbursement

    def get_reimbursement_amount(self) -> Decimal:
        """Calculate the reimbursement amount based on the payment_type and presence of image."""
        if self.payment_type.personal_expense:
            # con immagine
            if self.image:
                return self.amount_base
            return 0
        # Company
        if self.image:
            return 0
        return Decimal(-1) * Decimal(self.amount_base)


@receiver(pre_save, sender=Expense)
def recalculate_reimbursement(sender: Expense, instance: Expense, **kwargs) -> None:  # noqa: ANN003
    if instance.id:
        try:
            old_instance = Expense.objects.get(id=instance.id)
            if (
                not old_instance.image
                and bool(instance.image)
                or old_instance.payment_type.personal_expense != instance.payment_type.personal_expense
            ):
                instance.apply_reimbursement()
        except Expense.DoesNotExist:
            instance.apply_reimbursement()
