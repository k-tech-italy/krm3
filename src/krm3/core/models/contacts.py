from natural_keys import NaturalKeyModel
from django.db import models

from krm3.config import settings



class Client(NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ['name']

class SocialMedia(models.Model):
    url = models.URLField()

    def __str__(self) -> str:
        return self.url


class Phone(models.Model):
    number = models.CharField(max_length=16, unique=True)

    def __str__(self) -> str:
        return self.number


class Email(models.Model):
    address = models.EmailField()

    def __str__(self) -> str:
        return self.address


class Address(models.Model):
    address = models.CharField(max_length=500)

    def __str__(self) -> str:
        return self.address


class SocialMediaInfo(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE)
    social_media_url = models.ForeignKey(SocialMedia, on_delete=models.CASCADE)
    type = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.contact} - {self.social_media_url}"


class PhoneInfo(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE)
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE)
    type = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.contact} - {self.phone}"


class EmailInfo(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE)
    email = models.ForeignKey(Email, on_delete=models.CASCADE)
    type = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.contact} - {self.email}"


class AddressInfo(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    type = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.contact} - {self.address}"


class Contact(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Currently Active'
        LEFT_COMPANY = 'LEFT_COMPANY', 'Left Company'

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    tax_id = models.PositiveIntegerField(null=True, blank=True)
    job_title = models.CharField(max_length=80)
    picture = models.TextField(null=True, blank=True)
    internal_notes = models.TextField(null=True, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    social_media_urls = models.ManyToManyField(
        SocialMedia,
        through='SocialMediaInfo',
        related_name='contacts',
    )
    phones = models.ManyToManyField(
        Phone,
        through='PhoneInfo',
        related_name='contacts',
    )
    emails = models.ManyToManyField(
        Email,
        through='EmailInfo',
        related_name='contacts',
    )
    addresses = models.ManyToManyField(
        Address,
        through='AddressInfo',
        related_name='contacts',
    )

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"
