from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Self, override

from django.contrib.postgres.fields import DateRangeField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from natural_keys import NaturalKeyModel, NaturalKeyModelManager


from ...utils.dates import KrmDateRange
from .auth import Resource
from .contacts import Client

if TYPE_CHECKING:
    import datetime
    from decimal import Decimal

    from django.db.models.base import ModelBase
    from django.db.models.fields.related_descriptors import RelatedManager

    from krm3.core.models import InvoiceEntry, Mission, TaskEntry
    from krm3.core.models.auth import User


class PeriodBoundCheckerMixin:
    def save(
        self,
        *,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        self.full_clean()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def check_period_bounds(self):
        if self.period:
            if self.period.lower is None:
                raise ValidationError(_('"start_date" is required'), code='required')

            if self.period.upper and (self.period.lower >= self.period.upper):
                raise ValidationError(_('End date must be at least one day after start date'), code='invalid_date_interval')

    def clean(self) -> None:
        self.check_period_bounds()
        return super().clean()


class ProjectManager(NaturalKeyModelManager):
    def filter_acl(self, user: User) -> models.QuerySet[Project]:
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.can_manage_or_view_any_project():
            return self.all()
        return self.filter(mission__resource__profile__user=user)


class Project(PeriodBoundCheckerMixin, NaturalKeyModel):
    name = models.CharField(max_length=80, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    period = DateRangeField(help_text=_('N.B.: End date is the day after the actual end date'))
    metadata = models.JSONField(default=dict, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    objects = ProjectManager()

    mission_set: RelatedManager[Mission]

    class Meta:
        permissions = [
            ('view_any_project', "Can view(only) everybody's projects"),
            ('manage_any_project', "Can view, and manage everybody's projects"),
        ]

    def __str__(self) -> str:
        return str(self.name)

    def is_accessible(self, user: User) -> bool:
        return user.can_manage_or_view_any_project() or self.mission_set.filter(resource__profile__user=user).exists()


class POState(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class PO(PeriodBoundCheckerMixin, models.Model):
    """A PO for a project."""

    ref = models.CharField(max_length=50)
    is_billable = models.BooleanField(default=True)
    state = models.TextField(choices=POState, default=POState.OPEN)  # pyright: ignore[reportArgumentType]
    period = DateRangeField(help_text=_('N.B.: End date is the day after the actual end date'))

    project = models.ForeignKey(Project, on_delete=models.PROTECT)

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
        from krm3.core.models import TaskEntry

        time_entries = TaskEntry.objects.open().filter(task__in=self.tasks())  # pyright: ignore
        logged_hours = sum(entry.total_task_hours for entry in time_entries)
        return self.current_capacity() - logged_hours


class TaskQuerySet(models.QuerySet['Task']):
    def assigned_to(self, resource: Resource | int) -> Self:
        return self.filter(resource=resource)

    def filter_acl(self, user: User) -> Self:
        """Return the queryset for the owned records.

        Superuser gets them all.
        """
        if user.has_any_perm(
            'core.manage_any_project', 'core.view_any_project', 'core.manage_any_timesheet', 'core.view_any_timesheet'
        ):
            return self.all()
        return self.filter(resource__user=user)


class Task(PeriodBoundCheckerMixin, models.Model):
    """A task assigned to a resource."""

    title = models.CharField(max_length=200)
    basket_title = models.CharField(max_length=200, null=True, blank=True)
    color = models.CharField(null=True, blank=True)
    period = DateRangeField(help_text=_('N.B.: End date is the day after the actual end date'))
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
        time_entries: RelatedManager[TaskEntry]

    class Meta:
        ordering = ['project__name', 'title']
        permissions = [
            ('view_any_task_costs', "Can view(only) everybody's task costs"),
            ('manage_any_task_costs', "Can view, and manage everybody's task costs"),
        ]

    @override
    def __str__(self) -> str:
        return f'{self.project}: {self.title}'

    def clean(self) -> None:
        super().clean()
        if self.resource and self.period:
            from krm3.core.models import Contract

            try:
                Contract.objects.by_day_range(self.resource, self.period.lower, self.period.upper)
            except ValueError:
                raise ValidationError(_('Missing contract cover for the range {}').format(KrmDateRange(self.period)))
