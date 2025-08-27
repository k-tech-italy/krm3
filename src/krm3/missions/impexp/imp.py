import json
import tempfile
import zipfile

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import InMemoryUploadedFile
from pydantic_core._pydantic_core import ValidationError

from krm3.core.models import City, Client, Country, Project, Expense, ExpenseCategory, Mission, PaymentCategory
from krm3.currencies.models import Currency


class MissionImporter:
    def __init__(self, file: InMemoryUploadedFile) -> None:
        self.in_memory_file = file

    def store(self):
        """Stores the InMemoryUploadedFile to a tempfile for later processing."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            temp_file.write(self.in_memory_file.read())
            pathname = temp_file.name
        return pathname

    def validate(self):
        """Check if the InMemoryUploadedFile is a valid export file."""
        if not zipfile.is_zipfile(self.in_memory_file):
            raise ValidationError('Can only accept .zip files')
        with zipfile.ZipFile(self.in_memory_file, 'r') as zip_ref:
            if {'images/', 'data.json'} - set(zip_ref.namelist()):
                raise ValidationError('It oes not look like a valid Missions .zip file export')
        self.in_memory_file.seek(0)

    @staticmethod
    def get_data(pathname):
        def make_pk_as_int(data):
            """Convert pk to int when needed."""
            for f in [
                'clients',
                'countries',
                'projects',
                'cities',
                'resources',
                'categories',
                'payment_types',
                'missions',
                'expenses',
            ]:
                new_data = {int(k): v for k, v in data[f].items()}
                data[f] = new_data

        with zipfile.ZipFile(pathname) as zip_ref:
            data = json.loads(zip_ref.read('data.json'))
            make_pk_as_int(data)
        check_existing(Client, data, 'clients', ['name'])
        check_existing(Country, data, 'countries', ['name'])
        check_existing(Project, data, 'projects', ['name', ('client__name', 'clients')], amend=['notes'])
        check_existing(City, data, 'cities', ['name', ('country__name', 'countries')])
        check_existing(
            Currency,
            data,
            'currencies',
            ['title'],
            amend=['symbol', 'base', 'fractional_unit', 'decimals'],
            pkname='iso3',
        )
        check_existing(ExpenseCategory, data, 'categories', ['title'], amend=['active'], tree=True)
        check_existing(PaymentCategory, data, 'payment_types', ['title'], amend=['active'], tree=True)
        check_existing(
            Mission,
            data,
            'missions',
            ['number', 'year'],
            amend=[
                'title',
                ('from_date', lambda o: o.from_date.strftime('%Y-%m-%d')),
                ('to_date', lambda o: o.to_date.strftime('%Y-%m-%d')),
                ('default_currency', lambda o: o.default_currency.iso3),
            ],
        )
        check_existing(
            Expense,
            data,
            'expenses',
            [
                'day',
                'amount_currency',
                'amount_base',
                'amount_reimbursement',
                'detail',
                'created_ts',
                'modified_ts',
                'currency',
                'category',
                'payment_type',
                'document_type',
                'reimbursement',
            ],
            # TODO: calculate image checksum
        )

        return data


def check_existing(cls, data, entry_name, fields, amend=[], pkname='id', tree=False):
    """Check if target record exists.

    It will update with the id if the record exists.
    If the amend list is not empty it will try to flag the inbound data as EXISTS/ADD.

    data: is the index (dict) of the data being loaded
    entry_name: is the key in the data to look for
    fields: are the lookup fields
    amend: list of fields to match to determine EXISTS/AMEND
    """
    for pk, instance in data[entry_name].items():
        try:
            lookup = {}
            for f in fields:
                if isinstance(f, (list, tuple)):
                    f, data_lookup_name = f
                    model_name, field_name = f.split('__')
                    lookup[f] = data[data_lookup_name][instance[model_name]][field_name]
                else:
                    lookup[f] = instance[f]
            # Fetch target record based on lookups
            obj = cls.objects.get(**lookup)
            if tree:
                if str(obj) != instance['tree']:
                    raise ValidationError(f'Hierarchy mismatch for instance {instance}')
            for toamend in amend:
                if isinstance(toamend, (list, tuple)):  # we assume is a function returning the json repr
                    toamend, fx = toamend
                    value = fx(obj)
                else:
                    value = getattr(obj, toamend)
                if instance[toamend] != value:
                    instance['__check__'] = 'AMEND'
                    break
            else:
                instance['__check__'] = 'EXISTS'
            # assign the target pk in the data[entry_name]
            instance[pkname] = getattr(obj, pkname)
        except ObjectDoesNotExist:
            instance['__check__'] = 'ADD'
