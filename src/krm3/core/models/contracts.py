import datetime
import typing

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from krm3.missions.media import contract_directory_path
from krm3.utils.dates import DATE_INFINITE, KrmDay

if typing.TYPE_CHECKING:
    from krm3.core.models import Task


class Contract(models.Model):
    resource = models.ForeignKey('core.Resource', on_delete=models.CASCADE)
    period = DateRangeField(help_text='NB: End date is the day after the actual end date')
    country_calendar_code = models.CharField(
        null=True,
        blank=True,
        help_text='Country calendar code as per https://holidays.readthedocs.io/en/latest/#available-countries',
    )
    working_schedule = models.JSONField(blank=True, default=dict)
    meal_voucher = models.JSONField(blank=True, default=dict)
    comment = models.TextField(null=True, blank=True, help_text='Optional comment about the contract')
    document = models.FileField(
        upload_to=contract_directory_path,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf'])],
        help_text='Optional PDF document (PDF files only)',
    )

    class Meta:
        ordering = ('period',)
        constraints = [
            ExclusionConstraint(
                name='exclude_overlapping_contracts',
                expressions=[
                    ('period', RangeOperators.OVERLAPS),
                    ('resource', RangeOperators.EQUAL),
                ],
            )
        ]

    def __str__(self) -> str:
        if self.period.lower is None:
            return 'Invalid Contract (No start date)'
        if self.period.upper:
            end_dt = self.period.upper - datetime.timedelta(days=1)
            return f'{self.period.lower.strftime("%Y-%m-%d")} - {end_dt.strftime("%Y-%m-%d")}'
        return f'{self.period.lower.strftime("%Y-%m-%d")} - ...'

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()

        if self.period.lower is None:
            raise ValidationError({'period': 'Start date is required.'})
        if self.period.upper is not None and self.period.upper < self.period.lower + datetime.timedelta(days=1):
            raise ValidationError({'period': 'End date must be at least one day after start date.'})

    def falls_in(self, day: datetime.date | KrmDay) -> bool:
        """Check if the provided day falls into the contract period."""
        if isinstance(day, KrmDay):
            day = day.date
        if self.period.upper is None:
            return self.period.lower <= day
        return self.period.lower <= day < self.period.upper

    def get_tasks(self) -> list['Task']:
        """Return all tasks worked during this contract."""
        from krm3.core.models import Task  # noqa: PLC0415

        contract_interval = (
            self.period.lower,
            self.period.upper - datetime.timedelta(days=1) if self.period.upper else DATE_INFINITE,
        )

        ret = []
        for task in Task.objects.filter(resource=self.resource).order_by('start_date'):
            task_interval = (task.start_date, task.end_date or DATE_INFINITE)
            if (contract_interval[0] <= task_interval[0] <= contract_interval[1]) or (
                contract_interval[0] <= task_interval[1] <= contract_interval[1]
            ):
                ret.append(task)
        return ret
