from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.signals import post_save
from django.dispatch import receiver
from natural_keys.models import NaturalKeyModel

# User = get_user_model()


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **kwargs):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **kwargs)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, email, password=None, **kwargs):
        kwargs.setdefault('is_active', True)
        kwargs.setdefault('is_staff', True)
        kwargs.setdefault('is_superuser', True)
        if kwargs.get('is_active') is not True:
            raise ValueError('Superuser must be active')
        if kwargs.get('is_staff') is not True:
            raise ValueError('Superuser must be staff')
        if kwargs.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        return self.create_user(email, password, username=username, **kwargs)


class User(AbstractUser):
    objects = UserManager()

    @staticmethod
    def get_natural_key_fields():
        return ['username']


class Client(NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return str(self.name)


class Project(NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.name)


class Country(NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural = 'countries'


class City(NaturalKeyModel):
    name = models.CharField(max_length=80)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name)

    class Meta:
        constraints = (
            UniqueConstraint(
                fields=('name', 'country'),
                name='unique_city_in_country'),
        )
        verbose_name_plural = 'cities'


class UserProfile(NaturalKeyModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    picture = models.TextField()

    def __str__(self):
        return self.user.username


class Resource(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=50, help_text='Overwritten by profile.first_name if profile is provided',
                                  blank=True)
    last_name = models.CharField(max_length=50, help_text='Overwritten by profile.last_name if profile is provided',
                                 blank=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
