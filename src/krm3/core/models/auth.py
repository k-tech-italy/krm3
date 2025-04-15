from __future__ import annotations

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

    def can_manage_and_view_any_project(self) -> bool:
        """Check visibility and edit rights for privileged users.

        :return: `True` if the user is allowed to view and edit data on
            any project, `False` otherwise.
        """
        return (
            self.is_superuser
            or self.get_all_permissions().intersection({'core.manage_any_project', 'core.view_any_project'}) != set()
        )


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

    def __str__(self) -> str:
        return f'{self.first_name} {self.last_name}'


@receiver(post_save, sender=User)
def create_user_profile(sender: User, instance: User, created: bool, **kwargs: dict) -> None:
    if created:
        UserProfile.new(user=instance)
