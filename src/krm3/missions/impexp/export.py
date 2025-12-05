from __future__ import  annotations
import io
import json
import os
import shutil
import typing
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings

from krm3.core.models import City, Client, Country, ExpenseCategory, Mission, PaymentCategory, Project, Resource
from krm3.currencies.models import Currency
from krm3.missions.api.serializers.expense import ExpenseExportSerializer
from krm3.missions.api.serializers.mission import MissionSerializer
from krm3.missions.media import EXPENSES_IMAGE_PREFIX

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet, Model


def _add_data(data: dict, param: str, pk: int, data1: Model) -> int:
    """Add object data to dict."""
    if pk not in data[param]:
        if hasattr(data1, 'objects'):  # we assume a django model
            data1 = data1.objects.get(pk=pk)
            data1 = data1.default_serializer(data1, depth=0).data
        data[param][pk] = data1
        return data1
    return data[param][pk]


class MissionExporter:
    def __init__(self, queryset: QuerySet[Mission]) -> None:
        self.queryset = queryset

    def export(self) -> io.BytesIO:
        images_prefix_offset = len(f'{settings.MEDIA_URL}{EXPENSES_IMAGE_PREFIX}/')

        data = {
            'clients': {},
            'countries': {},
            'projects': {},
            'cities': {},
            'resources': {},
            'currencies': {},
            'categories': {},
            'payment_types': {},
            'missions': {},
            'expenses': {},
        }
        with TemporaryDirectory() as tempdir:
            os.mkdir(f'{tempdir}/images')
            mission: Mission

            for mission in self.queryset.all():
                serializer = MissionSerializer(mission, depth=0)

                _add_data(data, 'missions', mission.id, serializer.data)
                data['missions'][mission.id] = serializer.data

                _add_data(data, 'currencies', mission.default_currency_id, Currency)
                project = _add_data(data, 'projects', mission.project_id, Project)
                client = _add_data(data, 'clients', project['client'], Client)  # noqa: F841
                city = _add_data(data, 'cities', mission.city_id, City)
                country = _add_data(data, 'countries', city['country'], Country)  # noqa: F841
                resource = _add_data(data, 'resources', mission.resource_id, Resource)  # noqa: F841

                for expense in mission.expenses.all():
                    serializer = ExpenseExportSerializer(expense)
                    expense_data = _add_data(data, 'expenses', expense.id, serializer.data)
                    _add_data(data, 'currencies', expense.currency_id, Currency)
                    category = _add_data(data, 'categories', expense.category_id, ExpenseCategory)
                    category['tree'] = str(expense.category)
                    payment_type = _add_data(data, 'payment_types', expense.payment_type_id, PaymentCategory)
                    payment_type['tree'] = str(expense.payment_type)

                    # copy image
                    if expense_data['image']:
                        realpath = settings.MEDIA_ROOT + expense_data['image'][len(settings.MEDIA_URL) - 1 :]
                        if not Path(realpath).exists():
                            raise RuntimeWarning(
                                f'Critical error: file for expense {expense_data["id"]} not found at {realpath}'
                            )
                        shutil.copy(realpath, f'{tempdir}/images')
                        expense_data['image'] = expense_data['image'][images_prefix_offset:]

            with open(f'{tempdir}/data.json', 'w') as fo:
                fo.write(json.dumps(data))

            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                for root, _, files in os.walk(tempdir):
                    for file in files:
                        # Get the full path of the file on the filesystem
                        file_path = os.path.join(root, file)

                        # 'arcname' is the name the file will have INSIDE the zip.
                        # os.path.relpath removes the absolute temp path, keeping only
                        # the relative structure inside the zip.
                        arcname = os.path.relpath(file_path, tempdir)

                        archive.write(file_path, arcname=arcname)
            buffer.seek(0)
        return buffer
