# Generated by Django 4.2.2 on 2023-07-27 05:37

from django.db import migrations, models


def forward(apps, schema_editor):
    Currency = apps.get_model('currencies', 'Currency')
    for obj in Currency.objects.filter(iso3__in=['EUR', 'USD', 'GBP']):
        obj.active = True
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('currencies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='active',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
