# Generated by Django 5.2.2 on 2025-07-02 13:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_introducing_timesheet_model'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='resource',
            options={'ordering': ['first_name', 'last_name']},
        ),
        migrations.AlterModelOptions(
            name='task',
            options={'ordering': ['project__name', 'title'], 'permissions': [('view_any_task_costs', "Can view(only) everybody's task costs"), ('manage_any_task_costs', "Can view, and manage everybody's task costs")]},
        ),
    ]
