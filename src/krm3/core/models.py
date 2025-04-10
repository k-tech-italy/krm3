from __future__ import annotations

from typing import TYPE_CHECKING, Self, Any

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.signals import post_save
from django.dispatch import receiver
from natural_keys.models import NaturalKeyModel, NaturalKeyModelManager

from krm3.currencies.models import Currency

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager
    from krm3.missions.models import Mission


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **kwargs: Any) -> User:
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **kwargs)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username: str, email: str, password: str | None = None, **kwargs: Any) -> User:
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
    objects = UserManager()  # type: ignore
    picture = models.TextField(null=True, blank=True)
    social_profile = models.TextField(null=True, blank=True)

    @staticmethod
    def get_natural_key_fields() -> list[str]:
        return ['username']

    def can_manage_and_view_any_project(self) -> bool:
        """Check visibility and edit rights for privileged users.

        :return: `True` if the user is allowed to view and edit data on
            any project, `False` otherwise.
        """
        return (
            self.is_superuser
            or self.get_all_permissions().intersection({'core.manage_any_project', 'core.view_any_project'}) != set()
        )


class Client(NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self) -> str:
        return str(self.name)


class ProjectManager(NaturalKeyModelManager):
    def filter_acl(self, user: User) -> models.QuerySet[User]:
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.can_manage_and_view_any_project():
            return self.all()
        return self.filter(mission__resource__profile__user=user)


class Project(NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    objects = ProjectManager()

    if TYPE_CHECKING:
        mission_set: RelatedManager[Mission]

    def __str__(self) -> str:
        return str(self.name)

    def is_accessible(self, user: User) -> bool:
        if user.can_manage_and_view_any_project():
            return True
        return self.mission_set.filter(resource__profile__user=user).count() > 0

    class Meta:
        permissions = [
            ('view_any_project', "Can view(only) everybody's projects"),
            ('manage_any_project', "Can view, and manage everybody's projects"),
        ]


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


class UserProfile(NaturalKeyModel):
    """The Profile is used to record the user profile picture in social auth."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    picture = models.TextField(null=True, blank=True)
    social_profile = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.user.username

    @classmethod
    def new(cls, user: User) -> Self:
        return cls.objects.create(user=user)


class Resource(models.Model):
    """A person, e.g. an employee or external contractor."""

    profile = models.OneToOneField(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(
        max_length=50, help_text='Overwritten by profile.first_name if profile is provided', blank=True
    )
    last_name = models.CharField(
        max_length=50, help_text='Overwritten by profile.last_name if profile is provided', blank=True
    )

    def __str__(self) -> str:
        return f'{self.first_name} {self.last_name}'


@receiver(post_save, sender=User)
def create_user_profile(sender: User, instance: User, created: bool, **kwargs: dict) -> None:
    if created:
        UserProfile.new(user=instance)
