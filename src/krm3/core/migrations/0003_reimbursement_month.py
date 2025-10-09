from __future__ import annotations

import typing

from django.db import migrations, models

if typing.TYPE_CHECKING:
    from krm3.core.models import Reimbursement

_mapping = {
    'Gennaio': 'jan,gen',
    'Febbraio': 'feb',
    'Marzo': 'mar',
    'Aprile': 'apr',
    'Maggio': 'may,mag',
    'Giugno': 'jun,giu',
    'Luglio': 'jul,lug',
    'Agosto': 'aug,ago',
    'Settembre': 'sep,sett',
    'Ottobre': 'oct,ott',
    'Novembre': 'nov',
    'Dicembre': 'dec,dic',
}
mapping = {}
for k, v in _mapping.items():
    v = v.split(',')
    for vv in v:
        mapping[vv.lower()] = k


def match_month(title: str) -> str:
    for k, v in mapping.items():
        if k in title.lower():
            return v
    else:
        return None


def forward(apps, schema_editor):
    R: Reimbursement = apps.get_model('core', 'Reimbursement')
    for obj in R.objects.filter(month__isnull=True):
        obj: R
        title = obj.title.replace(obj.resource.last_name, '').replace(obj.resource.first_name, '')
        obj.month = match_month(title)
        obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_alter_timeentry_task'),
    ]

    operations = [
        migrations.AddField(
            model_name='reimbursement',
            name='month',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
