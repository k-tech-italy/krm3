from django.db.models import UniqueConstraint
from natural_keys import NaturalKeyModel
from django.db import models

from krm3.currencies.models import Currency


class Country(NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)
    default_currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name_plural = 'countries'


class City(NaturalKeyModel):
    name = models.CharField(max_length=80)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.name} ({self.country.name})'

    class Meta:
        constraints = (UniqueConstraint(fields=('name', 'country'), name='unique_city_in_country'),)
        verbose_name_plural = 'cities'
