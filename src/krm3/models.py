from django.db import models
from django.db.models import UniqueConstraint


class Client(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return str(self.name)


class Project(models.Model):
    name = models.CharField(max_length=80, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name)


class Country(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural = 'countries'


class City(models.Model):
    name = models.CharField(max_length=80)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name)

    class Meta:
        constraints = (
            UniqueConstraint(fields=('name', 'country'), name='unique_city_in_country'),
        )
        verbose_name_plural = 'cities'
