# Generated by Django 4.2.6 on 2023-12-11 16:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('currencies', '0002_currency_active'),
        ('missions', '0015_reimbursement_resource'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mission',
            name='default_currency',
            field=models.ForeignKey(blank=True, help_text='Leave blank for default [EUR]', on_delete=django.db.models.deletion.PROTECT, to='currencies.currency'),
        ),
        migrations.AddConstraint(
            model_name='mission',
            constraint=models.UniqueConstraint(fields=('number', 'year'), name='unique_mission_number_year'),
        ),
    ]
