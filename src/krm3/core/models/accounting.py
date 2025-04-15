from typing import override
from django.db import models

from .projects import Basket


class Invoice(models.Model):
    """Invoice data.

    Should be imported from an outside system (e.g. Odoo).
    """

    number = models.CharField(max_length=30)

    @override
    def __str__(self) -> str:
        return self.number


class InvoiceEntry(models.Model):
    """Models how many person-hours will be charged.

    These hours are taken from the related `basket`.
    """

    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='Number of hours to charge')

    basket = models.ForeignKey(Basket, on_delete=models.CASCADE, related_name='invoice_entries')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='entries')

    class Meta:
        verbose_name_plural = 'Invoice entries'

    @override
    def __str__(self) -> str:
        return f'Invoice {self.invoice} - entry #{self.pk}: {self.amount}h on basket {self.basket}'
