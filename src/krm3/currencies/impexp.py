import decimal
import json
from operator import itemgetter

import django_tables2 as tables
from django.core.files.uploadedfile import InMemoryUploadedFile

from krm3.currencies.models import Rate


class RateImporter:
    SESSION_KEY = 'rate_importer'

    @staticmethod
    def _build_table_class(currencies):
        return type('tables', (tables.Table, ), {k: tables.Column() for k in currencies})

    def __init__(self, request, from_session=False) -> None:
        self.request = request
        if not from_session:
            request.session.pop(RateImporter.SESSION_KEY, None)

    @property
    def _store(self):
        return self.request.session[RateImporter.SESSION_KEY]

    def store(self, in_memory_file: InMemoryUploadedFile):
        """Stores the InMemoryUploadedFile to a tempfile for later processing."""
        self.request.session[RateImporter.SESSION_KEY] = {
            'original': in_memory_file.read().decode('utf-8'), 'parsed': None
        }

    def get_data(self, sorting=None):
        data = self._store['parsed']
        if not data:
            data = self._store['parsed'] = json.loads(self._store['original'])

        currencies = self._get_currencies()

        header = ['day'] + list(currencies)
        data = [
            [d['pk']] +
            [d['fields']['rates'].get(f, '') for f in currencies]
            for d in data
        ]
        sortkey = 0 if sorting is None else header.index(sorting)
        data = sorted(data, key=itemgetter(sortkey), reverse=True)
        return [header] + data

    def _get_currencies(self):
        currencies = set()
        for d in self._store['parsed']:
            currencies |= set(d['fields']['rates'].keys())
        return currencies

    def preview(self, sorting=None):
        data = self.get_data(sorting)
        for d in data[1:]:
            rate = Rate.objects.filter(day=d[0]).first()
            if rate is None:
                d[0] = f'++ {d[0]}'
            else:
                for i, currency in enumerate(data[0]):
                    if v := rate.rates.get(currency, None) is None:
                        d[i+1] = f'++ {d[i+1]}'
                    elif decimal.Decimal(d[i+1]) != v:
                        d[i+1] = f'<> {d[i+1]}'
        return RateImporter._build_table_class(data[0])([dict(zip(data[0], z)) for z in data[1:]])

    def load(self):
        data = self.get_data()
        for x in data:
            pass
