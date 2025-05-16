from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Self, override, Iterable

# from django.contrib.auth import get_user_model  # noqa - see below
from django.db import models
from django.utils.translation import gettext_lazy as _
from natural_keys import NaturalKeyModel, NaturalKeyModelManager

from .auth import Resource
from .contacts import Client
from .timesheets import TimeEntry

if TYPE_CHECKING:
    from decimal import Decimal
    from krm3.core.models.auth import User
    from krm3.core.models import Project, Task, Mission, InvoiceEntry

    from django.contrib.auth.models import AbstractUser
    from django.db.models.fields.related_descriptors import RelatedManager


# FIXME: we cannot use a variable as a type hint
# User = get_user_model()  # noqa


class ProjectManager(NaturalKeyModelManager):
    def filter_acl(self, user: User) -> models.QuerySet['Project']:
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

    mission_set: RelatedManager[Mission]

    def __str__(self) -> str:
        return str(self.name)

    def is_accessible(self, user: User) -> bool:
        if user.can_manage_and_view_any_project():
            return True
        return self.mission_set.filter(resource__profile__user=user).count() > 0

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str = None,
        update_fields: Iterable[str] = None,
    ) -> None:
        if self.start_date is None:
            self.start_date = datetime.date.today()
        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        permissions = [
            ('view_any_project', "Can view(only) everybody's projects"),
            ('manage_any_project', "Can view, and manage everybody's projects"),
        ]


class POState(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class PO(models.Model):
    """A PO for a project."""

    ref = models.CharField(max_length=50)
    is_billable = models.BooleanField(default=True)
    state = models.TextField(choices=POState, default=POState.OPEN)  # pyright: ignore[reportArgumentType]
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    class Meta:
        constraints = (models.UniqueConstraint(fields=('ref', 'project'), name='unique_ref_project_in_po'),)
        verbose_name = 'PO'
        verbose_name_plural = 'POs'

    @override
    def __str__(self) -> str:
        return self.ref


class Basket(models.Model):
    """Defines the cumulative availability of person-hours for a PO."""

    title = models.CharField(max_length=200)
    initial_capacity = models.DecimalField(max_digits=10, decimal_places=2)
    # XXX: should we SET_NULL? or rather SET(next in line if any)?
    follows = models.OneToOneField('self', on_delete=models.RESTRICT, null=True, blank=True, related_name='followed_by')

    po = models.ForeignKey(PO, on_delete=models.CASCADE)

    invoice_entries: RelatedManager[InvoiceEntry]

    @override
    def __str__(self) -> str:
        return self.title

    def tasks(self) -> models.QuerySet[Task]:
        """Return the tasks attached to this basket.

        :return: a queryset of related `Task`s.
        """
        return Task.objects.filter(basket_title=self.title)

    def current_capacity(self) -> Decimal:
        """Compute the basket's current capacity based on invoiced hours.

        :return: the computed capacity
        """
        invoiced_hours = self.invoice_entries.values_list('amount', flat=True)
        return self.initial_capacity - sum(invoiced_hours)

    def current_projected_capacity(self) -> Decimal:
        """Compute the basket' current capacity.

        Calculations use both invoices and open time entries.

        :return: the computed capacity
        """
        time_entries = TimeEntry.objects.open().filter(task__in=self.tasks())  # pyright: ignore
        logged_hours = sum(entry.total_task_hours for entry in time_entries)
        return self.current_capacity() - logged_hours


class TaskQuerySet(models.QuerySet['Task']):
    def active_between(self, range_start: datetime.date, range_end: datetime.date) -> Self:
        return self.filter(start_date__lte=range_end).filter(
            models.Q(end_date=None) | models.Q(end_date__gte=range_start)
        )

    def assigned_to(self, resource: Resource | int) -> Self:
        return self.filter(resource=resource)

    def filter_acl(self, user: AbstractUser) -> Self:
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.is_superuser or user.get_all_permissions().intersection(
            {'core.manage_any_project', 'core.view_any_project'}
        ):
            return self.all()
        return self.filter(resource__user=user)


class Task(models.Model):
    """A task assigned to a resource."""

    title = models.CharField(max_length=200)
    basket_title = models.CharField(max_length=200, null=True, blank=True)
    # TODO: validate this
    color = models.CharField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    # TODO: make prices currency-aware
    work_price = models.DecimalField(max_digits=10, decimal_places=2)
    on_call_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    travel_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    overtime_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    # XXX: should we retain this instead?
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)

    objects = TaskQuerySet.as_manager()

    if TYPE_CHECKING:
        time_entries: RelatedManager[TimeEntry]

    @override
    def __str__(self) -> str:
        return self.title

    def time_entries_between(self, start: datetime.date, end: datetime.date) -> models.QuerySet[TimeEntry]:
        """Return all time entries between the two given dates.

        :param start: the date at the start of the range
        :param end: the date at the end of the range
        :return: a `QuerySet` of time entries
        """
        return self.time_entries.filter(date__range=(start, end))
