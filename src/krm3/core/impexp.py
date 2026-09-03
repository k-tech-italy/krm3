import io
import typing

from django.db.models import F

from krm3.core.models import TimesheetSubmission

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet

    from krm3.core.models.auth import Resource


class TimesheetExporter:
    """Resource timesheets historical exporter."""

    def __init__(self, queryset: 'QuerySet[Resource]') -> None:
        self.queryset = queryset


    def export(self) -> io.BytesIO:
        # get all TimesheetSubmission for the given queryset
        ts_qs = TimesheetSubmission.objects.select_related('resource'). \
            filter(resource__in=self.queryset, closed=True). \
            annotate(
                r_firstname=F('resource__first_name'),
                r_lastname=F('resource__first_name'),
                r_fiscal_code=F('resource__fiscal_code'),
            ). \
            order_by('resource_id', 'period')
        ts_map: dict[int, list[dict]] = {}
        for ts in ts_qs:
            ts_map_entry = ts_map.setdefault(ts.resource_id, [])
            ts_map_entry.append(ts.timesheet)

        return ts_map
