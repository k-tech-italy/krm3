# Generated by Django 4.2.4 on 2023-09-20 17:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('missions', '0013_alter_reimbursement_issue_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='reimbursement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expenses', to='missions.reimbursement'),
        ),
    ]
