import datetime

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models

from krm3.utils.dates import KrmDay

class Contract(models.Model):
    resource = models.ForeignKey('core.Resource', on_delete=models.CASCADE)
    period = DateRangeField(help_text='NB: End date is the day after the actual end date')
    country_calendar_code = models.CharField(
        null=True,
        blank=True,
        help_text='Country calendar code as per https://holidays.readthedocs.io/en/latest/#available-countries',
    )
    working_schedule = models.JSONField(blank=True, null=True)

    class Meta:
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
            return f'{self.period.lower.strftime('%Y-%m-%d')} - {end_dt.strftime('%Y-%m-%d')}'
        return f'{self.period.lower.strftime('%Y-%m-%d')} - ...'

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
