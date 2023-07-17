import json
import os
import shutil
from tempfile import NamedTemporaryFile, TemporaryDirectory

from django.conf import settings

from krm3.missions.api.serializers.expense import ExportExpenseSerializer
from krm3.missions.api.serializers.mission import ExportMissionSerializer
from krm3.missions.media import EXPENSES_IMAGE_PREFIX
from krm3.missions.models import ExpenseCategory, Mission, PaymentCategory


class MissionExporter:
    def __init__(self, queryset) -> None:
        self.queryset = queryset

    def export(self):  # noqa: C901
        images_prefix_offset = len(f'{settings.MEDIA_URL}{EXPENSES_IMAGE_PREFIX}/')

        data = {
            'clients': {}, 'countries': {}, 'projects': {}, 'cities': {}, 'resources': {},
            'currencies': {}, 'categories': {}, 'payment_types': {}, 'missions': [], 'expenses': []
        }
        with TemporaryDirectory() as tempdir:
            os.mkdir(f'{tempdir}/images')
            mission: Mission
            for mission in self.queryset.all():
                serializer = ExportMissionSerializer(mission)
                data['missions'].append(serializer.data)
                for expense in mission.expense_set.all():
                    serializer = ExportExpenseSerializer(expense, exclude={'mission'})
                    data['expenses'].append(serializer.data)

            for mission in data['missions']:
                if (id := mission['project']['id']) not in data['projects']:
                    if (client_id := mission['project']['client']['id']) not in data['clients']:
                        data['clients'][client_id] = mission['project']['client']
                        mission['project']['client'] = client_id
                    data['projects'][id] = mission['project']
                    mission['project'] = id
                if (id := mission['city']['id']) not in data['cities']:
                    if (country_id := mission['city']['country']['id']) not in data['countries']:
                        data['countries'][country_id] = mission['city']['country']
                        mission['city']['country'] = country_id
                    data['cities'][id] = mission['city']
                    mission['city'] = id
                if (id := mission['resource']['id']) not in data['resources']:
                    if mission['resource']['profile'] and mission['resource']['profile']['user']:
                        del mission['resource']['profile']['user']
                    data['resources'][id] = mission['resource']
                    mission['resource'] = id
                if (iso3 := mission['default_currency']['iso3']) not in data['currencies']:
                    data['currencies'][iso3] = mission['default_currency']
                    mission['default_currency'] = iso3

            for expense in data['expenses']:
                if (iso3 := expense['currency']['iso3']) not in data['currencies']:
                    data['currencies'][iso3] = expense['currency']
                expense['currency'] = iso3
                if (id := expense['category']['id']) not in data['categories']:
                    data['categories'][id] = expense['category']
                    tree = '.'.join(
                        [x.title for x in ExpenseCategory.objects.get(id=id).get_ancestors(include_self=False)])
                    del data['categories'][id]['parent']
                    data['categories'][id]['tree'] = tree
                expense['category'] = id
                if (id := expense['payment_type']['id']) not in data['payment_types']:
                    data['payment_types'][id] = expense['payment_type']
                    tree = '.'.join(
                        [x.title for x in PaymentCategory.objects.get(id=id).get_ancestors(include_self=False)])
                    del data['payment_types'][id]['parent']
                    data['payment_types'][id]['tree'] = tree
                expense['payment_type'] = id
                if expense['image']:
                    realpath = settings.MEDIA_ROOT + expense['image'][len(settings.MEDIA_URL)-1:]
                    shutil.copy(realpath, f'{tempdir}/images')
                    expense['image'] = expense['image'][images_prefix_offset:]

            with open(f'{tempdir}/data.json', 'w') as fo:
                fo.write(json.dumps(data))
            zipfile = NamedTemporaryFile().name
            shutil.make_archive(zipfile, 'zip', tempdir)
        return f'{zipfile}.zip'
