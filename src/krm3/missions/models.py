from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

# from krm3.currencies.models import Currency
from krm3.core.models import City, Project, Resource
from krm3.missions.media import mission_directory_path


class MissionManager(models.Manager):

    def owned(self, user):
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
                {'missions.manage_any_mission', 'missions.view_any_mission'}):
            return self
        return self.filter(resource__profile__user=user)


class Mission(models.Model):
    number = models.PositiveIntegerField(blank=True, help_text='Set automatically if left blank')
    title = models.CharField(max_length=50, null=True, blank=True)
    from_date = models.DateField()
    to_date = models.DateField()

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)

    objects = MissionManager()

    def __str__(self):
        title = self.title or self.city.name
        return f'{self.resource}, {title}, {self.number}'

    def clean(self):
        if self.to_date is not None and self.from_date is not None and self.to_date < self.from_date:
            raise ValidationError(_('to_date must be > from_date'))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.clean()
        super().save(force_insert, force_update, using, update_fields)

    def is_owner(self, user):
        if user.is_superuser or user.get_all_permissions().intersection(
                {'missions.manage_any_mission', 'missions.view_any_mission'}):
            return self
        return self.resource.profile and self.resource.profile.user == user

    class Meta:
        permissions = [
            ('view_any_mission', "Can view(only) everybody's missions"),
            ('manage_any_mission', "Can view, and manage everybody's missions"),
        ]


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
        permissions = [
            ('view_any_expense', "Can view(only) everybody's expenses"),
            ('manage_any_expense', "Can view, and manage everybody's expenses"),
        ]
        constraints = (
            UniqueConstraint(
                fields=('title', 'parent'),
                name='unique_expense_category_title'),
        )


class PaymentCategory(MPTTModel):
    title = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
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
    issue_date = models.DateField()


class ExpenseManager(models.Manager):
    def by_otp(self, otp: str):
        """Retrieve the instance matching the provided otp."""
        ref = settings.FERNET_KEY.decrypt(f'gAAAAA{otp}').decode()
        expense_id, mission_id, ts = ref.split('|')
        return self.get(mission_id=mission_id, id=expense_id, modified_date=ts)

    def owned(self, user):
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
                {'missions.manage_any_expense', 'missions.view_any_expense'}):
            return self
        return self.filter(mission__resource__profile__user=user)

    def is_owner(self, user):
        if user.is_superuser or user.get_all_permissions().intersection(
                {'missions.manage_any_expense', 'missions.view_any_expense'}):
            return self
        return self.resource.profile and self.resource.profile.user == user


class Expense(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    day = models.DateField()
    amount_currency = models.DecimalField(max_digits=10, decimal_places=2, help_text='Amount in currency')
    amount_base = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text=f'Amount in {settings.CURRENCY_BASE}')
    amount_reimbursement = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                               help_text='Reimbursed amount')
    detail = models.CharField(max_length=100, null=True, blank=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    payment_type = models.ForeignKey(PaymentCategory, on_delete=models.PROTECT)
    reimbursement = models.ForeignKey(Reimbursement, on_delete=models.SET_NULL, null=True, blank=True)

    image = models.FileField(upload_to=mission_directory_path, null=True, blank=True)

    # currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    objects = ExpenseManager()

    def is_owner(self, user):
        if user.is_superuser or user.get_all_permissions().intersection(
                {'missions.manage_any_expense', 'missions.view_any_expense'}):
            return self
        return self.mission.resource.profile and self.mission.resource.profile.user == user

    def get_otp(self):
        return settings.FERNET_KEY.encrypt(
            f'{self.id}|{self.mission_id}|{self.modified_date}'.encode()).decode('utf-8')[6:]

    def check_otp(self, otp: str):
        ref = settings.FERNET_KEY.decrypt(f'gAAAAA{otp}').decode()
        expense_id, mission_id, ts = ref.split('|')
        return f'{self.modified_date}' == ts and self.id == int(expense_id) and self.mission_id == int(mission_id)

    def __str__(self):
        return f'{self.day}, {self.amount_currency} for {self.category}'
