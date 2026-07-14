import datetime
from collections.abc import Iterable
from decimal import Decimal

from constance import config
from django.conf import settings
from django.db import models

from krm3.currencies import client as rates_service

from krm3.utils.currencies import rounding
from krm3.utils.queryset import ActiveQuerySet


class Currency(models.Model):
    title = models.CharField(max_length=30, unique=True)
    symbol = models.CharField(max_length=10)
    decimals = models.IntegerField(null=True, blank=True)
    iso3 = models.CharField(max_length=3, primary_key=True)
    fractional_unit = models.CharField(max_length=20)
    base = models.PositiveIntegerField()
    active = models.BooleanField(default=False)

    objects = ActiveQuerySet.as_manager()

    class Meta:
        verbose_name_plural = 'currencies'
        ordering = ('iso3',)

    def __str__(self) -> str:
        return f'{self.iso3} {self.symbol}'

    def is_base(self) -> bool:
        return self.iso3 == settings.BASE_CURRENCY


class Rate(models.Model):
    day = models.DateField(primary_key=True)
    rates = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f'{self.day:%Y-%m-%d}'

    # FIXME: force what?
    def ensure_rates(self, force: bool = False, include: Iterable[str] | None = None) -> None:
        """Ensure the rates are present for the currencies.

        If `force` is `True`, all rates are reset and recomputed.
        """
        if include is None:
            include = []

        if force:
            missing = set(config.CURRENCIES.split(',')) | set(include) | set(self.rates.keys())
        else:
            missing = (set(config.CURRENCIES.split(',')) | set(include)) - set(self.rates.keys())

        if missing:
            # FIXME: why `get_client()` when we are calling an OXR-specific API?
            response = rates_service.get_client().get_historical(self.day.strftime('%Y-%m-%d'), symbols=sorted(missing))
            self.rates |= {
                currency: rate
                for currency, rate in response['rates'].items()
                # FIXME: USD rate is always rewritten, might invalidate existing conversion rates
                if currency == 'USD' or currency in missing
            }
            self.save()

    # FIXME: force what?
    def get_rates(self, force: bool = False, include: Iterable[str] | None = None) -> dict:
        """Update the exchange rates and retrieve the ones in `included`.

        If `force` is `True`, all rates are reset and recomputed.
        """
        if include is None:
            include = []

        self.ensure_rates(force=force, include=include)
        return {currency: rate for currency, rate in self.rates.items() if currency in config.CURRENCIES.split(',')}

    def convert(
        self, from_value: int | float | Decimal, from_currency: str, to_currency: str = None, force: bool = False
    ) -> Decimal:
        """Convert a value from a specific currency to another.

        If the target currency is not specified, use `settings.BASE_CURRENCY`.

        If `force` is `True`, all rates are reset and recomputed.
        """
        if isinstance(from_currency, Currency):
            from_currency = from_currency.iso3
        if isinstance(to_currency, Currency):
            to_currency = to_currency.iso3
        if to_currency is None:
            to_currency = settings.BASE_CURRENCY
        self.ensure_rates(force=force, include=[from_currency, to_currency])
        return rounding(to_currency, float(from_value) / self.rates[from_currency] * self.rates[to_currency])

    @staticmethod
    def for_date(date: datetime.date, force: bool = False, include: Iterable[str] | None = None) -> Decimal:
        """Return the `Rate` for the given date.

        If `force` is `True`, all rates are reset (if applicable) and
        recomputed.

        Factory method.
        """
        if include is None:
            include = []
        rate, _ = Rate.objects.get_or_create(day=date)
        rate.ensure_rates(force=force, include=include)
        return rate
