from natural_keys import NaturalKeyModel
from django.db import models


class Client(NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ['name']
