# import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

# from krm3.currencies.models import Currency
from krm3.core.models import City, Project, Resource


class Mission(models.Model):
    number = models.PositiveIntegerField(blank=True, help_text='Set automatically if left blank')
    title = models.CharField(max_length=50, null=True, blank=True)
    from_date = models.DateField()
    to_date = models.DateField()

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)

    def __str__(self):
        title = self.title or self.city.name
        return f'{self.resource}, {title}, {self.number}'

    def clean(self):
        if self.to_date < self.from_date:
            raise ValidationError(_('to_date must be > from_date'))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.clean()
        super().save(force_insert, force_update, using, update_fields)


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


class Expense(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    day = models.DateField()
    amount_currency = models.DecimalField(max_digits=10, decimal_places=2, help_text='Amount in currency')
    amount_base = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text=f'Amount in {settings.CURRENCY_BASE}')
    amount_reimbursement = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                               help_text='Reimbursed amount')
    detail = models.CharField(max_length=100)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    payment_type = models.ForeignKey(PaymentCategory, on_delete=models.PROTECT)
    reimbursement = models.ForeignKey(Reimbursement, on_delete=models.SET_NULL, null=True, blank=True)

    image = models.FileField()
    # currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.day}, {self.amount_currency} for {self.category}'
