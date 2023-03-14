from django.conf import settings
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

# from krm3.currencies.models import Currency
from krm3.core.models import City, Project, Resource


class Mission(models.Model):
    from_date = models.DateField()
    to_date = models.DateField()

    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    resource = models.ForeignKey(Resource, on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.id} {self.from_date} -- {self.to_date}'


class ExpenseCategory(MPTTModel):
    title = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name_plural = 'expense categories'


class PaymentCategory(MPTTModel):
    title = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name_plural = 'payment categories'


class Reimbursement(models.Model):
    title = models.CharField(max_length=50)
    issue_date = models.DateField()


class Expense(models.Model):
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
    # currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
