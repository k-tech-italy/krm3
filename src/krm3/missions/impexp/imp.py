import json
import tempfile
import zipfile

from django.core.files.uploadedfile import InMemoryUploadedFile
from pydantic_core._pydantic_core import ValidationError

from krm3.core.models import City, Client, Country, Project
from krm3.currencies.models import Currency


class MissionImporter:
    def __init__(self, file: InMemoryUploadedFile) -> None:
        self.in_memory_file = file

    def store(self):
        """Stores the InMemoryUploadedFile to a tempfile for later processing."""
        pathname = tempfile.mktemp(suffix='.zip')
        with open(pathname, 'wb') as fo:
            fo.write(self.in_memory_file.read())
        # default_storage.save(pathname, ContentFile(self.in_memory_file.read()))
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
        with zipfile.ZipFile(pathname) as zip_ref:
            data = json.loads(zip_ref.read('data.json'))
        check_existing(Client, data, 'clients', ['name'])
        check_existing(Country, data, 'countries', ['name'])
        check_existing(Project, data, 'projects', ['name', 'notes'])
        check_existing(City, data, 'cities', ['name', ('country__name', 'countries')])
        check_existing(Currency, data, 'currencies', ['name', 'title', 'symbol', 'base'])

        return data


def check_existing(cls, data, entry_name, fields, pkname='id'):
    for pk, instance in data[entry_name].items():
        try:
            lookup = {}
            for f in fields:
                if isinstance(f, (list, tuple)):
                    f, data_lookup_name = f
                    model_name, field_name = f.split('__')
                    lookup[f] = data[data_lookup_name][str(instance[model_name])][field_name]
                else:
                    lookup[f] = instance[f]
            obj = cls.objects.get(**lookup)
            instance['__check__'] = 'EXISTS'
            instance[pkname] = getattr(obj, pkname)
        except Client.DoesNotExists:
            instance['__check__'] = 'ADD'
