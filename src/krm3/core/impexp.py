import io
import json
import os
import typing
import zipfile
from io import BytesIO
from tempfile import TemporaryDirectory

from django.db.models import F

from krm3.core.models import TimeEntry, TimesheetSubmission

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet

    from krm3.core.models.auth import Resource


class TimesheetExporter:
    """Resource timesheets historical exporter."""
    def __init__(self, queryset: 'QuerySet[Resource]'):
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

        # # get all TimesheetEntries for the given queryset
        # te_qs = TimeEntry.objects.filter(resource__in=queryset).order_by('resource_id', 'date')
        # te_list = []
        # for te in te_qs:
        #
        #     pass
        # buffer: BytesIO = io.BytesIO()
        # buffer.write(json.dumps(ts_map, indent=2, ensure_ascii=False).encode('utf-8'))
        # buffer.seek(0)

        # with TemporaryDirectory() as tempdir:
        #     buffer: BytesIO = io.BytesIO()
        #     with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        #         for root, _, files in os.walk(tempdir):
        #             for file in files:
        #                 # Get the full path of the file on the filesystem
        #                 file_path = os.path.join(root, file)
        #
        #                 # 'arcname' is the name the file will have INSIDE the zip.
        #                 # os.path.relpath removes the absolute temp path, keeping only
        #                 # the relative structure inside the zip.
        #                 arcname = os.path.relpath(file_path, tempdir)
        #
        #                 archive.write(file_path, arcname=arcname)
        #     buffer.seek(0)
        return ts_map
