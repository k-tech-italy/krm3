import datetime

from django.conf import settings
from django.db import models

from ...utils.currencies import rounding
from ...utils.queryset import ActiveQuerySet


class Currency(models.Model):
    title = models.CharField(max_length=30, unique=True)
    symbol = models.CharField(max_length=10)
    decimals = models.IntegerField(null=True, blank=True)
    iso3 = models.CharField(max_length=3, primary_key=True)
    fractional_unit = models.CharField(max_length=20)
    base = models.PositiveIntegerField()
    active = models.BooleanField(default=False)

    objects = ActiveQuerySet.as_manager()

    def __str__(self):
        return f'{self.iso3} {self.symbol}'

    class Meta:
        verbose_name_plural = 'currencies'
        ordering = ('iso3', )


class Rate(models.Model):
    day = models.DateField(primary_key=True)
    rates = models.JSONField(default=dict)

    def __str__(self):
        return f'{self.day:%Y-%m-%d}'

    def ensure_rates(self, force=False, include=None):
        """Ensure the rates are present for the currencies. Forces refresh eventually"""
        if include is None:
            include = []

        missing = set(settings.CURRENCIES) | set(include) - set(self.rates.keys())

        if force:
            missing = set(settings.CURRENCIES) | set(include) | set(self.rates.keys())
        if missing:
            from krm3.currencies.client import get_client
            client = get_client()
            ret = client.get_historical(
                self.day.strftime('%Y-%m-%d'),
                symbols=list(missing))
            self.rates = ret['rates']
            self.save()

    def get_rates(self, force=False, include=None):
        """Retrieves the rate values. Forces the refresh if needed"""
        if include is None:
            include = []

        self.ensure_rates(force=force, include=include)
        return {k: v for k, v in self.rates.items() if k in settings.CURRENCIES}

    def convert(self, from_value, from_currency: str, to_currency: str = settings.CURRENCY_BASE, force=False):
        """Converts a value from a specific currency to another.
        If target currency is not specified it will be using settings.CURRENCY_BASE"""
        if isinstance(from_currency, Currency):
            from_currency = from_currency.iso3
        if isinstance(to_currency, Currency):
            to_currency = to_currency.iso3
        self.ensure_rates(force=force, include=[from_currency, to_currency])
        return rounding(to_currency, float(from_value) / self.rates[from_currency] * self.rates[to_currency])

    def to_base(self, from_value, from_currency: str, force=False):
        """Converts a value from a specific currency to base currency"""
        return self.convert(from_value, from_currency, settings.CURRENCY_BASE, force)

    @staticmethod
    def for_date(date: datetime.date, include=None):
        """Constructor-like method returning a Rate instance for the specific date."""
        if include is None:
            include = []
        rate, _ = Rate.objects.get_or_create(day=date)
        rate.ensure_rates(include=include)
        return rate
