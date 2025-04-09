import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, override

from django.core import exceptions
from django.db import models
from django.dispatch import receiver
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

    ref = models.CharField(max_length=50)
    is_billable = models.BooleanField(default=True)
    state = models.TextField(choices=POState, default=POState.OPEN)  # type: ignore
    start_date = models.DateField(default=_DEFAULT_START_DATE)
    end_date = models.DateField(null=True, blank=True)

    project = models.ForeignKey(core_models.Project, on_delete=models.CASCADE)

    class Meta:
        constraints = (models.UniqueConstraint(fields=('ref',), name='unique_ref_in_po'),)
        verbose_name = 'PO'
        verbose_name_plural = 'POs'

    @override
    def __str__(self) -> str:
        return self.ref


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

        :raises NotImplementedError: TODO
        :return: the computed capacity
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


class TimeEntryState(models.TextChoices):
    """The state of a timesheet entry."""

    OPEN = 'OPEN', _('Open')
    CLOSED = 'CLOSED', _('Closed')


class TimeEntry(models.Model):
    """A timesheet entry."""

    date = models.DateField()
    last_modified = models.DateTimeField(auto_now=True)
    work_hours = models.DecimalField(max_digits=4, decimal_places=2)
    sick_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    holiday_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    leave_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    on_call_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    travel_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    rest_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    state = models.TextField(choices=TimeEntryState, default=TimeEntryState.OPEN)  # type: ignore
    comment = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, null=True, blank=True)

    resource = models.ForeignKey(core_models.Resource, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Time entries'

    @override
    def __str__(self) -> str:
        return f'{self.date}: {self.resource} on "{self.task}" ({self.state})'

    @override
    def clean(self) -> None:
        errors = []

        is_work_day = any(
            hours > 0.0
            for hours in (
                self.work_hours,
                self.leave_hours,
                self.overtime_hours,
                self.on_call_hours,
                self.rest_hours,
                self.travel_hours,
            )
        )
        is_sick_day = self.sick_hours > 0.0
        is_holiday = self.holiday_hours > 0.0

        if is_sick_day and is_holiday:
            errors.append(
                exceptions.ValidationError(
                    _('You cannot log more than one type of full-day absences in a day.'),
                    code='multiple_full_day_absence_hours',
                )
            )

        is_full_day_absence = is_sick_day or is_holiday
        if is_work_day and is_full_day_absence:
            errors.append(
                exceptions.ValidationError(
                    _('You cannot log work-related hours on %(what)s.'),
                    params={'what': _('a sick day') if is_sick_day else _('a holiday')},
                    code='work_during_full_day_absence',
                )
            )

        if errors:
            raise exceptions.ValidationError(errors)


@receiver(models.signals.pre_save, sender=TimeEntry)
def validate_time_entry(sender: TimeEntry, instance: TimeEntry, **kwargs: Any) -> None:
    instance.clean()
