# Generated by Django 4.2.2 on 2023-08-28 11:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('missions', '0009_documenttype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='document_type',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='missions.documenttype'),
            preserve_default=False,
        ),
    ]
