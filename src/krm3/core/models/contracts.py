import datetime

from django.contrib.postgres.fields import DateRangeField

from django.db import models


class Contract(models.Model):
    resource = models.ForeignKey("core.Resource", on_delete=models.CASCADE)
    period = DateRangeField(help_text='NB: End date is the day after the actual end date')
    country_calendar = models.CharField()
    working_schedule = models.JSONField(blank=True, null=True)

    def __str__(self) -> str:
        end_dt = self.period.upper - datetime.timedelta(days=1)
        return f'{self.period.lower.strftime('%Y-%m-%d')} - {end_dt.strftime('%Y-%m-%d')}'
