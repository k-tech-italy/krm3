from __future__ import annotations

from decimal import Decimal
import typing
from django.contrib.auth.base_user import BaseUserManager
from natural_keys import NaturalKeyModel
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **kwargs: typing.Any) -> User:
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **kwargs)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username: str, email: str, password: str | None = None, **kwargs: typing.Any) -> User:
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

    def get_resource(self) -> 'Resource':
        """Return the associated resource or None if not available."""
        try:
            resource = self.resource
        except self.__class__.resource.RelatedObjectDoesNotExist:
            resource = None
        return resource

    def can_manage_or_view_any_project(self) -> bool:
        """Check if user has RO/RW permissions for any project.

        :return: `True` if the user is allowed to view or edit data on projects for any resource,
           `False` otherwise.
        """
        return self.has_any_perm('core.manage_any_project', 'core.view_any_project')

    def has_any_perm(self, *perms: str) -> bool:
        """Check that the user has at least one of the given permissions.

        :param : the permissions to check
        :return: `True` if the user has at least one of the given
          `perms`, `False` otherwise.
        """
        return any(self.has_perm(perm) for perm in perms)


class UserProfile(NaturalKeyModel):
    """The Profile is used to record the user profile picture in social auth."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    picture = models.TextField(null=True, blank=True)
    social_profile = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.user.username

    @classmethod
    def new(cls, user: User) -> typing.Self:
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
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['first_name', 'last_name']

    def __str__(self) -> str:
        return f'{self.first_name} {self.last_name}'

    @property
    def daily_work_hours_max(self) -> Decimal:
        """Maximum number of hours a resource should work each day.

        It can be exceeded.

        :return: the maximum number of hours in a work day.
        """
        return Decimal(8)


@receiver(post_save, sender=User)
def create_user_profile(sender: User, instance: User, created: bool, **kwargs: dict) -> None:
    if created:
        UserProfile.new(user=instance)
