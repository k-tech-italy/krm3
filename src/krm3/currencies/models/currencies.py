from django.conf import settings
from django.db import models

from ...utils.currencies import rounding


class Currency(models.Model):
    title = models.CharField(max_length=30, unique=True)
    symbol = models.CharField(max_length=10)
    decimals = models.IntegerField(null=True, blank=True)
    iso3 = models.CharField(max_length=3, primary_key=True)
    fractional_unit = models.CharField(max_length=20)
    base = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.iso3} {self.symbol} {self.title}'

    class Meta:
        verbose_name_plural = 'currencies'
        ordering = ('iso3', )


class Rate(models.Model):
    day = models.DateField(primary_key=True)
    rates = models.JSONField(default=dict)

    def __str__(self):
        return f'{self.day:%Y-%m-%d}'

    def _ensure_rates(self, force=False):
        """Ensure the rates are present for the currencies. Forces refresh eventually"""
        obj = Rate.objects.filter(day=self.day).first()
        if obj:
            self.rates = obj.rates
        missing = set(settings.CURRENCIES) - set(self.rates.keys())

        if force:
            missing = set(settings.CURRENCIES) | set(self.rates.keys())
        if missing:
            from krm3.currencies.client import get_client
            client = get_client()
            ret = client.get_historical(
                self.day.strftime('%Y-%m-%d'),
                symbols=list(missing))
            self.rates = ret['rates']
            self.save()

    def get_rates(self, force=False):
        """Retrieves the rate values. Forces the refresh if needed"""
        self._ensure_rates(force=force)
        return {k: v for k, v in self.rates.items() if k in settings.CURRENCIES}

    def convert(self, from_value, from_currency: str, to_currency: str = None, force=False):
        """Converts a value from a specific currency to another.
        If target currency is not specified it will be using settings.CURRENCY_BASE"""
        if to_currency is None:
            to_currency = settings.CURRENCY_BASE
        self._ensure_rates(force=force)
        return rounding(to_currency, float(from_value) / self.rates[from_currency] * self.rates[to_currency])

    def to_base(self, from_value, from_currency: str, force=False):
        """Converts a value from a specific currency to base currency"""
        return self.convert(from_value, from_currency, settings.CURRENCY_BASE, force)
