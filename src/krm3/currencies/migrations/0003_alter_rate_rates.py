# Generated by Django 5.0.2 on 2024-04-20 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('currencies', '0002_currency_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rate',
            name='rates',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]