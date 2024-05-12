import itertools
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

# from krm3.currencies.models import Currency
from krm3.core.models import City, Project, Resource
from krm3.currencies.models import Currency, Rate
from krm3.missions.exceptions import AlreadyReimbursed
from krm3.missions.media import mission_directory_path
from krm3.utils.queryset import ActiveManagerMixin


class MissionManager(ActiveManagerMixin, models.Manager):

    def filter_acl(self, user):
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
                {'missions.manage_any_mission', 'missions.view_any_mission'}):
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
        blank=True, null=True, help_text="Leave blank for defaulting to from_date's year")

    default_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, blank=True, null=True,
                                         help_text=f'Leave blank for default [{settings.BASE_CURRENCY}]')

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)

    objects = MissionManager()

    @staticmethod
    def calculate_number(instance_id: int | None, year: int) -> int:
        qs = Mission.objects.filter(
            number__isnull=False, year=year,
            status__in=[Mission.MissionStatus.SUBMITTED, Mission.MissionStatus.CANCELLED]
        )
        if instance_id:
            qs = qs.exclude(pk=instance_id)
        nums = [0] + sorted(list(qs.values_list('number', flat=True)))
        ret = list(
            itertools.takewhile(lambda v: v[0] == 0 or v[1] == nums[v[0] - 1] + 1, enumerate(nums))
        )[-1]
        return ret[1] + 1

    @property
    def expense_count(self):
        return self.expenses.count()

    def __str__(self):
        title = self.title or self.city.name
        return f'{self.resource}, {title}, {self.number}'

    def clean(self):
        if (self.number and self.status == Mission.MissionStatus.DRAFT) or \
                (self.number is None and self.status != Mission.MissionStatus.DRAFT):
            raise ValidationError(
                _('If a mission is in DRAFT then number must empty, otherwise it is mandatory'),
                code='number'
            )
        if self.to_date is not None and self.from_date is not None and self.to_date < self.from_date:
            raise ValidationError(_('to_date must be > from_date'))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.full_clean()
        super().save(force_insert, force_update, using, update_fields)

    def is_accessible(self, user) -> bool:
        if user.is_superuser or user.get_all_permissions().intersection(
                {'missions.manage_any_mission', 'missions.view_any_mission'}):
            return True
        return bool(self.resource and self.resource.user == user)

    class Meta:
        permissions = [
            ('view_any_mission', "Can view(only) everybody's missions"),
            ('manage_any_mission', "Can view, and manage everybody's missions"),
        ]
        constraints = [
            UniqueConstraint(fields=('number', 'year'), name='unique_mission_number_year')
        ]


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
        constraints = (
            UniqueConstraint(
                fields=('title', 'parent'),
                name='unique_expense_category_title'),
        )


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
        constraints = (
            UniqueConstraint(
                fields=('title', 'parent'),
                name='unique_payment_category_title'),
        )


class Reimbursement(models.Model):
    title = models.CharField(max_length=50)
    issue_date = models.DateField(auto_now_add=True)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)
    paid_date = models.DateField(blank=True, null=True)

    @property
    def expense_count(self):
        return self.expenses.count()

    def __str__(self):
        data = datetime.strftime(self.issue_date, '%Y-%m-%d')
        return f'{self.title} {data}'


class ExpenseManager(ActiveManagerMixin, models.Manager):
    def by_otp(self, otp: str):
        """Retrieve the instance matching the provided otp."""
        ref = settings.FERNET_KEY.decrypt(f'gAAAAA{otp}').decode()
        expense_id, mission_id, ts = ref.split('|')
        return self.get(mission_id=mission_id, id=expense_id, modified_ts=ts)

    def filter_acl(self, user):
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
                {'missions.manage_any_expense', 'missions.view_any_expense'}):
            return self.all()
        return self.filter(mission__resource__user_id=user.id)


class Expense(models.Model):
    mission = models.ForeignKey(Mission, related_name='expenses', on_delete=models.CASCADE)
    day = models.DateField()
    amount_currency = models.DecimalField(max_digits=10, decimal_places=2, help_text='Amount in currency')
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, blank=True,
                                 help_text='Leave blank to inherit from mission.default_currency')
    amount_base = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text=f'Amount in {settings.BASE_CURRENCY}')
    amount_reimbursement = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                               help_text='Reimbursed amount')
    detail = models.CharField(max_length=100, null=True, blank=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    payment_type = models.ForeignKey(PaymentCategory, on_delete=models.PROTECT)
    reimbursement = models.ForeignKey(Reimbursement, related_name='expenses',
                                      on_delete=models.SET_NULL, null=True, blank=True)

    image = models.FileField(upload_to=mission_directory_path, null=True, blank=True)

    created_ts = models.DateTimeField(auto_now_add=True)
    modified_ts = models.DateTimeField(auto_now=True)

    objects = ExpenseManager()

    def get_updated_millis(self):
        return int(self.modified_ts.timestamp() * 1000)

    def is_accessible(self, user) -> bool:
        if user.is_superuser or user.get_all_permissions().intersection(
                {'missions.manage_any_expense', 'missions.view_any_expense'}):
            return True
        return bool(self.mission.resource and self.mission.resource.user == user)

    def get_otp(self):
        return settings.FERNET_KEY.encrypt(
            f'{self.id}|{self.mission_id}|{self.modified_ts}'.encode()).decode('utf-8')[6:]

    def check_otp(self, otp: str):
        ref = settings.FERNET_KEY.decrypt(f'gAAAAA{otp}').decode()
        expense_id, mission_id, ts = ref.split('|')
        return f'{self.modified_ts}' == ts and self.id == int(expense_id) and self.mission_id == int(mission_id)

    def calculate_base(self, force_rates=False, force_reset=False, save=True):
        """(Re)calculate the base amount."""
        if force_reset or self.amount_base is None:
            # we need to recalculate it
            if self.currency.is_base():
                self.amount_base = self.amount_currency
            else:
                self.amount_base = Rate.for_date(
                    self.day, force=force_rates).convert(self.amount_currency, self.currency)
            if save:
                self.save()
        return self.amount_base

    def calculate_reimbursement(self, force=False, save=True):
        if self.reimbursement and not force:
            raise AlreadyReimbursed(f'Expense {self.id} already reimbursed in {self.reimbursement_id}')
        if force or self.amount_reimbursement is None:
            self.calculate_base(save=False)
            # Personale
            if self.payment_type.personal_expense:
                # con immagine
                if self.image:
                    self.amount_reimbursement = self.amount_base
                else:
                    self.amount_reimbursement = 0
            # Aziendale
            else:
                if self.image:
                    self.amount_reimbursement = 0
                else:
                    self.amount_reimbursement = Decimal(-1) * Decimal(self.amount_base)
            if save:
                self.save()
        return self.amount_reimbursement

    def __str__(self):
        return f'{self.day}, {self.amount_currency} for {self.category}'

    class Meta:
        permissions = [
            ('view_any_expense', "Can view(only) everybody's expenses"),
            ('manage_any_expense', "Can view, and manage everybody's expenses"),
        ]
