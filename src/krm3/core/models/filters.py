from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

if TYPE_CHECKING:
    from krm3.core.models.auth import User


class SavedFilterManager(models.Manager['SavedFilter']):
    def filter_acl(self, user: User) -> models.QuerySet[SavedFilter]:
        """Return the filters saved by the user: saved filters are personal, even for superusers."""
        if not user.is_authenticated:
            return self.none()
        return self.filter(user=user)


class SavedFilter(models.Model):
    """A set of filter values a user saved with a name, for one page or table of the frontend."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_filters')
    page = models.CharField(max_length=100, help_text='The page or table the filter applies to, e.g. "missions"')
    name = models.CharField(max_length=100)
    values = models.JSONField(default=dict, blank=True, help_text='Filter field name -> value or list of values')
    summary = models.TextField(
        blank=True, default='', help_text='The filter as people read it, e.g. "Resource: Jane Roe; From: 2025-01-01"'
    )
    url = models.CharField(
        max_length=2000, blank=True, default='', help_text='Frontend address that opens the page with this filter'
    )
    is_default = models.BooleanField(
        default=False, help_text='Applied when the page is loaded without filters; at most one per user and page'
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = SavedFilterManager()

    class Meta:
        ordering = ['page', 'name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'page', 'name'], name='unique_saved_filter_name_per_page'),
            models.UniqueConstraint(
                fields=['user', 'page'], condition=models.Q(is_default=True), name='one_default_saved_filter_per_page'
            ),
        ]

    def __str__(self) -> str:
        return f'{self.page}: {self.name}'

    def display_values(self) -> list[tuple[str, str]]:
        """Return (field, value) pairs to show the filter to people; lists are joined with commas."""
        return [
            (field, ', '.join(value) if isinstance(value, list) else str(value)) for field, value in self.values.items()
        ]
