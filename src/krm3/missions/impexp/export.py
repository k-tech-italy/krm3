import json
import os
import shutil
from tempfile import NamedTemporaryFile, TemporaryDirectory

from django.conf import settings

from krm3.core.models import City, Client, Country, Project, Resource
from krm3.currencies.models import Currency
from krm3.missions.api.serializers.expense import ExpenseSerializer
from krm3.missions.api.serializers.mission import MissionSerializer
from krm3.missions.media import EXPENSES_IMAGE_PREFIX
from krm3.missions.models import ExpenseCategory, Mission, PaymentCategory


def _add_data(data, param, id, data1):
    if id not in data[param]:
        if hasattr(data1, 'objects'):  # we assume a django model
            data1 = data1.objects.get(pk=id)
            data1 = data1.default_serializer(data1, depth=0).data
        data[param][id] = data1
        return data1
    else:
        return data[param][id]


class MissionExporter:
    def __init__(self, queryset) -> None:
        self.queryset = queryset

    def export(self):
        images_prefix_offset = len(f'{settings.MEDIA_URL}{EXPENSES_IMAGE_PREFIX}/')

        data = {
            'clients': {}, 'countries': {}, 'projects': {}, 'cities': {}, 'resources': {},
            'currencies': {}, 'categories': {}, 'payment_types': {}, 'missions': {}, 'expenses': {}
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
                    serializer = ExpenseSerializer(expense, exclude=['mission'], depth=0)
                    expense_data = _add_data(data, 'expenses', expense.id, serializer.data)
                    _add_data(data, 'currencies', expense.currency_id, Currency)
                    category = _add_data(data, 'categories', expense.category_id, ExpenseCategory)
                    category['tree'] = str(expense.category)
                    payment_type = _add_data(data, 'payment_types', expense.payment_type_id, PaymentCategory)
                    payment_type['tree'] = str(expense.payment_type)

                    # copy image
                    if expense_data['image']:
                        realpath = settings.MEDIA_ROOT + expense_data['image'][len(settings.MEDIA_URL)-1:]
                        shutil.copy(realpath, f'{tempdir}/images')
                        expense_data['image'] = expense_data['image'][images_prefix_offset:]

            # for k, mission in data['missions'].items():
            #     # reference project
            #     if (id := mission['project']['id']) not in data['projects']:
            #         if (client_id := mission['project']['client']['id']) not in data['clients']:
            #             data['clients'][client_id] = mission['project']['client']
            #             mission['project']['client'] = client_id
            #         data['projects'][id] = mission['project']
            #         mission['project'] = id
            #
            #     # reference city
            #     if (id := mission['city']['id']) not in data['cities']:
            #         if (country_id := mission['city']['country']['id']) not in data['countries']:
            #             data['countries'][country_id] = mission['city']['country']
            #             mission['city']['country'] = country_id
            #         data['cities'][id] = mission['city']
            #         mission['city'] = id
            #
            #     # reference resource
            #     if (id := mission['resource']['id']) not in data['resources']:
            #         if mission['resource']['profile'] and mission['resource']['profile']['user']:
            #             del mission['resource']['profile']['user']
            #         data['resources'][id] = mission['resource']
            #         mission['resource'] = id
            #
            #     # reference currency
            #     if (iso3 := mission['default_currency']['iso3']) not in data['currencies']:
            #         data['currencies'][iso3] = mission['default_currency']
            #         mission['default_currency'] = iso3
            #
            # for k, expense in data['expenses'].items():
            #     # reference currency
            #     if (iso3 := expense['currency']['iso3']) not in data['currencies']:
            #         data['currencies'][iso3] = expense['currency']
            #     expense['currency'] = iso3
            #
            #     # reference category
            #     if (id := expense['category']['id']) not in data['categories']:
            #         data['categories'][id] = expense['category']
            #         tree = str(ExpenseCategory.objects.get(id=id))
            #         del data['categories'][id]['parent']
            #         data['categories'][id]['tree'] = tree
            #     expense['category'] = id
            #
            #     # reference payment_type
            #     if (id := expense['payment_type']['id']) not in data['payment_types']:
            #         data['payment_types'][id] = expense['payment_type']
            #         tree = str(PaymentCategory.objects.get(id=id))
            #         del data['payment_types'][id]['parent']
            #         data['payment_types'][id]['tree'] = tree
            #     expense['payment_type'] = id
            #

            with open(f'{tempdir}/data.json', 'w') as fo:
                fo.write(json.dumps(data))
            zipfile = NamedTemporaryFile().name
            shutil.make_archive(zipfile, 'zip', tempdir)
        return f'{zipfile}.zip'
