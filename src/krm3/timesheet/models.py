import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, override

from django.db import models
from django.utils.translation import gettext_lazy as _

from krm3.core import models as core_models

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager

    from krm3.accounting.models import InvoiceEntry


class POState(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class PO(models.Model):
    """A PO for a project."""

    _DEFAULT_START_DATE = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)

    ref = models.CharField(max_length=50, null=True, blank=True)
    state = models.TextField(choices=POState, default=POState.OPEN)  # type: ignore
    start_date = models.DateField(default=_DEFAULT_START_DATE)
    end_date = models.DateField(null=True, blank=True)

    project = models.ForeignKey(core_models.Project, on_delete=models.CASCADE)

    class Meta:
        # NOTE: only works on PostgreSQL 15+
        constraints = (models.UniqueConstraint(fields=('ref',), name='unique_ref_in_po', nulls_distinct=True),)
        verbose_name = 'PO'
        verbose_name_plural = 'POs'

    @override
    def __str__(self) -> str:
        return self.ref or f'Internal (#{self.pk})'

    def is_billable(self) -> bool:
        """Check whether the PO is billable.

        POs without a `ref` are internal, therefore they cannot be
        billed to a client.

        :return: `True` if the PO is billable, `False` otherwise.
        """
        return bool(self.ref)

    def is_open(self) -> bool:
        """Check whether the PO is open.

        :return: `True` if this PO is open, `False` otherwise.
        """
        return self.state == POState.OPEN


class Basket(models.Model):
    """Defines the cumulative availability of person-hours for a PO."""

    title = models.CharField(max_length=200)
    initial_capacity = models.DecimalField(max_digits=10, decimal_places=2)

    po = models.ForeignKey(PO, on_delete=models.CASCADE)

    if TYPE_CHECKING:
        invoice_entries: RelatedManager[InvoiceEntry]

    @override
    def __str__(self) -> str:
        return self.title

    def current_capacity(self) -> Decimal:
        """Compute the basket's current capacity based on invoiced hours.

        :raises NotImplementedError: TODO
        :return: the computed capacity
        """
        raise NotImplementedError('TODO: implement current_capacity')

    def current_projected_capacity(self) -> Decimal:
        """Compute the basket' current capacity.

        Calculations use both invoices and time entries.

        :raises NotImplementedError:
        :return:
        """
        raise NotImplementedError('TODO: implement current_projected_capacity')


class Task(models.Model):
    """A task assigned to a resource."""

    title = models.CharField(max_length=200)
    basket_title = models.CharField(max_length=200, null=True, blank=True)
    # TODO: validate this
    color = models.TextField(max_length=6, null=True, blank=True)

    project = models.ForeignKey(core_models.Project, on_delete=models.CASCADE)
    # XXX: should we retain this instead?
    resource = models.ForeignKey(core_models.Resource, on_delete=models.CASCADE)

    @override
    def __str__(self) -> str:
        return self.title

    def baskets(self) -> models.QuerySet[Basket]:
        return Basket.objects.filter(title=self.basket_title)


class TimeEntryCategory(models.TextChoices):
    """Qualifier for a timesheet entry.

    Denotes how the `Resource` spent the time logged on the time sheet
    (e.g. normal work, overtime).
    """

    WORK = 'WORK', _('Work')
    TRAVEL = 'TRAVEL', _('Travel')
    OVERTIME = 'OVERTIME', _('Overtime')
    ON_CALL = 'ON CALL', _('On call')


class TimeEntryState(models.TextChoices):
    """The state of a timesheet entry."""

    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class TimeEntry(models.Model):
    """A timesheet entry."""

    date = models.DateField()
    category = models.TextField(choices=TimeEntryCategory, default=TimeEntryCategory.WORK)  # type: ignore
    last_modified = models.DateTimeField(auto_now=True)
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2)
    state = models.TextField(choices=TimeEntryState, default=TimeEntryState.OPEN)  # type: ignore
    comment = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, null=True, blank=True)

    # XXX: should we keep this instead?
    resource = models.ForeignKey(core_models.Resource, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Time entries'

    @override
    def __str__(self) -> str:
        return f'{self.date}: {self.resource} on "{self.task}" ({self.state})'
