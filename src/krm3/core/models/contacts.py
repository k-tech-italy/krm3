from natural_keys import NaturalKeyModel
from django.db import models

from krm3.config import settings



class Client(NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)
    picture = models.URLField(null=True, blank=True, help_text='Picture URL')

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        ordering = ['name']

class Website(models.Model):
    url = models.URLField(unique=True)

    def __str__(self) -> str:
        return self.url


class Phone(models.Model):
    number = models.CharField(unique=True)

    def __str__(self) -> str:
        return self.number


class Email(models.Model):
    address = models.EmailField(unique=True)

    def __str__(self) -> str:
        return self.address


class Address(models.Model):
    address = models.CharField(unique=True)

    def __str__(self) -> str:
        return self.address


class WebsiteInfo(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE)
    website = models.ForeignKey(Website, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.contact} - {self.website}"


class PhoneInfo(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE)
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE)
    kind = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.contact} - {self.phone}"


class EmailInfo(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE)
    email = models.ForeignKey(Email, on_delete=models.CASCADE)
    kind = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.contact} - {self.email}"


class AddressInfo(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    kind = models.CharField(max_length=80, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.contact} - {self.address}"


class Contact(models.Model):

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    tax_id = models.CharField(null=True, blank=True)
    job_title = models.CharField(max_length=80)
    picture = models.TextField(null=True, blank=True, help_text='Picture URL')
    internal_notes = models.TextField(null=True, blank=True)
    company = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    websites = models.ManyToManyField(
        Website,
        through='WebsiteInfo',
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

    def fetch_picture(self) -> None:
        if self.user and self.user.profile and self.user.profile.picture:
            self.picture = self.user.profile.picture
            self.save()
